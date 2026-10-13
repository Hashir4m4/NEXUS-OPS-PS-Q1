"""
VQC Leak-Free Preprocessing Module
==================================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 5D)

Implements leakage-safe preprocessing pipelines for the Variational Quantum
Classifier (VQC) with strict partition isolation:

1. Protocol A (LORO Cross-Validation):
   - Fold 1: Fits QuantumFeatureScaler exclusively on Record 106 raw features;
             transforms Record 106 (train) and Record 119 (validation).
   - Fold 2: Fits QuantumFeatureScaler exclusively on Record 119 raw features;
             transforms Record 119 (train) and Record 106 (validation).
   - Strict Isolation: Never uses precomputed *_scaled columns from features_train.csv
     during LORO. Always fits dynamically on raw FEATURE_NAMES to eliminate
     inter-patient validation leakage.

2. Protocol B (Final Model Benchmark):
   - Fits QuantumFeatureScaler on all 200 raw training beats (Records 106 & 119).
   - Transforms training beats (Records 106 & 119).
   - Transforms held-out test beats (Records 200 & 208) without fitting or refitting.
   - Strict Quarantine: Test data never influences scaler parameters.

3. Diagnostics & Quality Control:
   - Tracks element-level and beat-level clipping statistics for every partition.
   - Validates that transformed matrices strictly lie within [0, pi] with no NaNs/Infs.
   - Preserves sample ordering, binary labels, record IDs, and segment IDs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.feature_extraction import FEATURE_NAMES
from src.feature_scaling import QuantumFeatureScaler


@dataclass
class PreprocessedPartition:
    """
    Container holding preprocessed feature matrices, ground-truth labels,
    provenance metadata, and empirical clipping statistics for a single partition.
    """
    name: str
    record_ids: List[int]
    X: np.ndarray  # Shape (N, 6), float64, bounded in [0, pi]
    y: np.ndarray  # Shape (N,), int64, labels in {0, 1}
    segment_ids: List[str]
    annotation_symbols: List[str]
    clipping_stats: Dict[str, Any]
    scaler: Optional[QuantumFeatureScaler] = None

    def __post_init__(self):
        # Integrity validations
        if self.X.ndim != 2 or self.X.shape[1] != len(FEATURE_NAMES):
            raise ValueError(
                f"Feature matrix X must have shape (N, {len(FEATURE_NAMES)}), got {self.X.shape}"
            )
        if len(self.y) != len(self.X):
            raise ValueError(f"Label count ({len(self.y)}) does not match sample count ({len(self.X)})")
        if len(self.segment_ids) != len(self.X):
            raise ValueError("Segment ID count does not match sample count.")
        if np.isnan(self.X).any():
            raise ValueError(f"NaN values detected in feature matrix for partition '{self.name}'.")
        if np.isinf(self.X).any():
            raise ValueError(f"Infinite values detected in feature matrix for partition '{self.name}'.")
        if (self.X < 0.0).any() or (self.X > np.pi).any():
            raise ValueError(f"Feature values outside [0, pi] detected for partition '{self.name}'.")


@dataclass
class LOROFoldData:
    """Container for a single Leave-One-Record-Out (LORO) cross-validation fold."""
    fold_id: int
    train: PreprocessedPartition
    val: PreprocessedPartition
    scaler: QuantumFeatureScaler


@dataclass
class VQCPreprocessedBundle:
    """Comprehensive container encapsulating both LORO CV folds and final benchmark partitions."""
    fold1: LOROFoldData
    fold2: LOROFoldData
    final_train: PreprocessedPartition
    final_test: PreprocessedPartition
    final_scaler: QuantumFeatureScaler


def compute_clipping_statistics(
    X_raw: np.ndarray,
    scaler: QuantumFeatureScaler,
    feature_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Computes rigorous element-wise and beat-wise clipping statistics
    resulting from projecting raw features into the scaler's linear domain.

    Parameters
    ----------
    X_raw : np.ndarray
        Raw unscaled feature matrix of shape (N, n_features).
    scaler : QuantumFeatureScaler
        Fitted scaler with data_min_, data_max_, target_min, target_max, scale_.
    feature_names : Optional[List[str]]
        Names of the features. Defaults to FEATURE_NAMES.

    Returns
    -------
    Dict[str, Any]
        Dictionary detailing lower-bound, upper-bound, element-level,
        and beat-level clipping counts and rates.
    """
    if not scaler.is_fitted:
        raise RuntimeError("Scaler must be fitted to compute clipping statistics.")

    if feature_names is None:
        feature_names = FEATURE_NAMES

    X_mat = np.asarray(X_raw, dtype=float)
    if X_mat.ndim != 2 or X_mat.shape[1] != len(scaler.data_min_):
        raise ValueError(f"Shape mismatch: X_raw shape {X_mat.shape} vs scaler features {len(scaler.data_min_)}")

    n_samples, n_features = X_mat.shape

    # Compute unclipped continuous projection
    z = scaler.target_min + (X_mat - scaler.data_min_) * scaler.scale_

    lower_mask = z < scaler.target_min
    upper_mask = z > scaler.target_max
    any_clipped_mask = lower_mask | upper_mask

    feature_stats: Dict[str, Dict[str, int]] = {}
    lower_clipped_per_feat = lower_mask.sum(axis=0)
    upper_clipped_per_feat = upper_mask.sum(axis=0)

    for i, fn in enumerate(feature_names):
        feature_stats[fn] = {
            "lower_clipped": int(lower_clipped_per_feat[i]),
            "upper_clipped": int(upper_clipped_per_feat[i]),
            "total_clipped": int(lower_clipped_per_feat[i] + upper_clipped_per_feat[i]),
        }

    total_clipped_values = int(any_clipped_mask.sum())
    total_evaluated_values = int(n_samples * n_features)
    clipping_rate_values_pct = float(total_clipped_values / total_evaluated_values * 100.0) if total_evaluated_values > 0 else 0.0

    affected_beats_count = int(any_clipped_mask.any(axis=1).sum())
    affected_beats_pct = float(affected_beats_count / n_samples * 100.0) if n_samples > 0 else 0.0

    return {
        "n_samples": n_samples,
        "n_features": n_features,
        "total_evaluated_values": total_evaluated_values,
        "total_clipped_values": total_clipped_values,
        "clipping_rate_values_pct": round(clipping_rate_values_pct, 4),
        "affected_beats_count": affected_beats_count,
        "affected_beats_pct": round(affected_beats_pct, 4),
        "by_feature": feature_stats,
    }


def preprocess_dataframe_partition(
    df: pd.DataFrame,
    scaler: QuantumFeatureScaler,
    partition_name: str,
    feature_names: Optional[List[str]] = None
) -> PreprocessedPartition:
    """
    Transforms a single DataFrame partition using an existing, fitted scaler,
    capturing metadata, labels, and clipping statistics.

    Parameters
    ----------
    df : pd.DataFrame
        Source DataFrame containing raw feature columns and segment metadata.
    scaler : QuantumFeatureScaler
        Pre-fitted scaler instance.
    partition_name : str
        Descriptive label for the partition.
    feature_names : Optional[List[str]]
        List of raw feature column names to extract. Defaults to FEATURE_NAMES.

    Returns
    -------
    PreprocessedPartition
        Encapsulated partition with transformed X in [0, pi] and diagnostics.
    """
    if feature_names is None:
        feature_names = FEATURE_NAMES

    # Verify that raw feature columns are strictly present
    missing_features = [fn for fn in feature_names if fn not in df.columns]
    if missing_features:
        raise KeyError(f"DataFrame is missing required raw features: {missing_features}")

    # Extract raw features strictly (never accessing *_scaled)
    X_raw = df[feature_names].to_numpy(dtype=float)

    # Compute clipping statistics before transformation
    clipping_stats = compute_clipping_statistics(X_raw, scaler, feature_names=feature_names)

    # Transform to [0, pi] with clipping enforced
    X_scaled = scaler.transform(X_raw)

    # Extract metadata preserving exact row order
    y = df["label"].to_numpy(dtype=int)
    record_ids = [int(r) for r in df["record_id"]]
    segment_ids = [str(s) for s in df["segment_id"]]
    annotation_symbols = [str(a) for a in df["annotation_symbol"]]

    return PreprocessedPartition(
        name=partition_name,
        record_ids=record_ids,
        X=X_scaled,
        y=y,
        segment_ids=segment_ids,
        annotation_symbols=annotation_symbols,
        clipping_stats=clipping_stats,
        scaler=scaler,
    )


def prepare_loro_fold(
    df_train: pd.DataFrame,
    train_record: int,
    val_record: int,
    fold_id: int,
    feature_names: Optional[List[str]] = None
) -> LOROFoldData:
    """
    Prepares a single LORO cross-validation fold with strict patient isolation.

    Protocol A enforcement:
    - Isolates train_sub (record_id == train_record) and val_sub (record_id == val_record).
    - Instantiates a fresh QuantumFeatureScaler(target_min=0.0, target_max=pi, clip=True).
    - Fits scaler EXCLUSIVELY on train_sub raw features.
    - Transforms train_sub and val_sub using this fresh scaler.
    - Zero data from val_sub influences the scaler parameters.

    Parameters
    ----------
    df_train : pd.DataFrame
        Training DataFrame containing both training records.
    train_record : int
        Record ID designated for training in this fold (e.g. 106 or 119).
    val_record : int
        Record ID designated for validation in this fold (e.g. 119 or 106).
    fold_id : int
        Identifier for the fold (1 or 2).
    feature_names : Optional[List[str]]
        List of raw feature names. Defaults to FEATURE_NAMES.

    Returns
    -------
    LOROFoldData
        Complete fold container with train and validation partitions.
    """
    if feature_names is None:
        feature_names = FEATURE_NAMES

    # Partition by record_id
    train_sub = df_train[df_train["record_id"].astype(int) == train_record].copy().reset_index(drop=True)
    val_sub = df_train[df_train["record_id"].astype(int) == val_record].copy().reset_index(drop=True)

    if len(train_sub) == 0:
        raise ValueError(f"No records found for train_record={train_record}")
    if len(val_sub) == 0:
        raise ValueError(f"No records found for val_record={val_record}")

    # Fresh scaler fitted exclusively on training patient raw features
    fold_scaler = QuantumFeatureScaler(target_min=0.0, target_max=np.pi, clip=True)
    fold_scaler.fit(train_sub[feature_names])

    # Preprocess both partitions using the fold-specific scaler
    train_partition = preprocess_dataframe_partition(
        df=train_sub,
        scaler=fold_scaler,
        partition_name=f"LORO Fold {fold_id} Train (Record {train_record})",
        feature_names=feature_names,
    )
    val_partition = preprocess_dataframe_partition(
        df=val_sub,
        scaler=fold_scaler,
        partition_name=f"LORO Fold {fold_id} Val (Record {val_record})",
        feature_names=feature_names,
    )

    return LOROFoldData(
        fold_id=fold_id,
        train=train_partition,
        val=val_partition,
        scaler=fold_scaler,
    )


def prepare_loro_datasets(
    train_source: Union[pd.DataFrame, Path, str],
    feature_names: Optional[List[str]] = None
) -> Dict[int, LOROFoldData]:
    """
    Constructs both LORO cross-validation folds under Protocol A.

    Fold 1: Train Record 106 -> Validate Record 119
    Fold 2: Train Record 119 -> Validate Record 106

    Parameters
    ----------
    train_source : Union[pd.DataFrame, Path, str]
        DataFrame or path to features_train.csv.
    feature_names : Optional[List[str]]
        Raw feature column names.

    Returns
    -------
    Dict[int, LOROFoldData]
        Dictionary mapping fold_id (1, 2) to LOROFoldData.
    """
    if isinstance(train_source, (str, Path)):
        df_train = pd.read_csv(train_source)
    else:
        df_train = train_source.copy()

    fold1 = prepare_loro_fold(df_train, train_record=106, val_record=119, fold_id=1, feature_names=feature_names)
    fold2 = prepare_loro_fold(df_train, train_record=119, val_record=106, fold_id=2, feature_names=feature_names)

    return {1: fold1, 2: fold2}


def prepare_final_benchmark_datasets(
    train_source: Union[pd.DataFrame, Path, str],
    test_source: Union[pd.DataFrame, Path, str],
    feature_names: Optional[List[str]] = None
) -> Tuple[PreprocessedPartition, PreprocessedPartition, QuantumFeatureScaler]:
    """
    Constructs the final model training and held-out test evaluation partitions
    under Protocol B.

    Protocol B enforcement:
    - Fits QuantumFeatureScaler on all 200 raw training samples (Records 106 + 119).
    - Transforms training cohort.
    - Transforms held-out test cohort (Records 200 + 208) without fitting or updating parameters.
    - Test features never influence scaler parameters.

    Parameters
    ----------
    train_source : Union[pd.DataFrame, Path, str]
        Training DataFrame or path to features_train.csv.
    test_source : Union[pd.DataFrame, Path, str]
        Test DataFrame or path to features_test.csv.
    feature_names : Optional[List[str]]
        Raw feature column names.

    Returns
    -------
    Tuple[PreprocessedPartition, PreprocessedPartition, QuantumFeatureScaler]
        (final_train_partition, final_test_partition, final_scaler)
    """
    if feature_names is None:
        feature_names = FEATURE_NAMES

    if isinstance(train_source, (str, Path)):
        df_train = pd.read_csv(train_source)
    else:
        df_train = train_source.copy()

    if isinstance(test_source, (str, Path)):
        df_test = pd.read_csv(test_source)
    else:
        df_test = test_source.copy()

    # Fit scaler on full 200-sample raw training cohort
    final_scaler = QuantumFeatureScaler(target_min=0.0, target_max=np.pi, clip=True)
    final_scaler.fit(df_train[feature_names])

    train_partition = preprocess_dataframe_partition(
        df=df_train,
        scaler=final_scaler,
        partition_name="Final Full Train (Records 106 & 119)",
        feature_names=feature_names,
    )
    test_partition = preprocess_dataframe_partition(
        df=df_test,
        scaler=final_scaler,
        partition_name="Final Quarantined Test (Records 200 & 208)",
        feature_names=feature_names,
    )

    return train_partition, test_partition, final_scaler


def prepare_all_vqc_datasets(
    data_dir: Union[Path, str] = Path("data") / "processed"
) -> VQCPreprocessedBundle:
    """
    High-level entry point that loads features_train.csv and features_test.csv
    and constructs both LORO folds and the final benchmark partitions.

    Parameters
    ----------
    data_dir : Union[Path, str]
        Path to processed features directory.

    Returns
    -------
    VQCPreprocessedBundle
        Complete bundle ready for VQC training and evaluation routines.
    """
    data_path = Path(data_dir)
    train_path = data_path / "features_train.csv"
    test_path = data_path / "features_test.csv"

    if not train_path.exists():
        raise FileNotFoundError(f"Training features not found at {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Test features not found at {test_path}")

    df_train = pd.read_csv(train_path)
    df_test = pd.read_csv(test_path)

    loro_dict = prepare_loro_datasets(df_train)
    final_train, final_test, final_scaler = prepare_final_benchmark_datasets(df_train, df_test)

    return VQCPreprocessedBundle(
        fold1=loro_dict[1],
        fold2=loro_dict[2],
        final_train=final_train,
        final_test=final_test,
        final_scaler=final_scaler,
    )
