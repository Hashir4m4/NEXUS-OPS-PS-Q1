"""
Quantum Feature Scaling Module
==============================
NEXUS-OPS | PS-Q1: Biomedical Signal Classifier (Milestone 3)

Implements leakage-safe min-max feature normalization mapped to the quantum
rotational angle domain [0, pi] for parameterized quantum circuits (VQC / angle encoding).

Leakage Protection Rules:
-------------------------
1. The scaler MUST be fitted exclusively on training set features (Records 106 & 119).
2. Test partition features (Records 200 & 208) MUST NOT influence any min, max, or scale parameter.
3. Out-of-bound test points resulting from inter-subject distribution shifts are clipped
   safely into [0, pi] to respect valid quantum rotation bounds.
4. Constant features (zero variance) are detected and handled without division by zero.
"""

from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


class QuantumFeatureScaler:
    """
    Min-Max feature normalizer mapping continuous feature dimensions
    into the quantum rotational domain [0, pi].
    """

    def __init__(
        self,
        target_min: float = 0.0,
        target_max: float = np.pi,
        clip: bool = True,
        eps: float = 1e-12
    ):
        self.target_min = float(target_min)
        self.target_max = float(target_max)
        self.clip = clip
        self.eps = eps

        # Fitted parameters (initialized to None)
        self.feature_names: Optional[List[str]] = None
        self.data_min_: Optional[np.ndarray] = None
        self.data_max_: Optional[np.ndarray] = None
        self.data_range_: Optional[np.ndarray] = None
        self.scale_: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        feature_names: Optional[List[str]] = None
    ) -> "QuantumFeatureScaler":
        """
        Fits the scaler parameters (min and max per column) strictly on training data.

        Parameters
        ----------
        X : Union[np.ndarray, pd.DataFrame]
            Training feature matrix of shape (n_train_samples, n_features).
        feature_names : Optional[List[str]]
            List of feature column names.

        Returns
        -------
        QuantumFeatureScaler
            Fitted scaler instance.
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names = list(X.columns)
            X_mat = X.to_numpy(dtype=float)
        else:
            X_mat = np.asarray(X, dtype=float)
            self.feature_names = feature_names

        if X_mat.ndim != 2:
            raise ValueError(f"Expected 2D feature matrix, got shape {X_mat.shape}")

        self.data_min_ = np.min(X_mat, axis=0)
        self.data_max_ = np.max(X_mat, axis=0)
        raw_range = self.data_max_ - self.data_min_

        # Safe handling of constant features (avoid division by zero)
        is_constant = raw_range <= self.eps
        safe_range = np.where(is_constant, 1.0, raw_range)

        self.data_range_ = safe_range
        self.scale_ = (self.target_max - self.target_min) / safe_range
        self.is_fitted = True

        return self

    def transform(
        self,
        X: Union[np.ndarray, pd.DataFrame]
    ) -> np.ndarray:
        """
        Transforms features into [0, pi] using strictly training-learned parameters.

        Parameters
        ----------
        X : Union[np.ndarray, pd.DataFrame]
            Feature matrix to scale.

        Returns
        -------
        np.ndarray
            Scaled features strictly within [0, pi].
        """
        if not self.is_fitted:
            raise RuntimeError("QuantumFeatureScaler must be fitted before transforming.")

        if isinstance(X, pd.DataFrame):
            X_mat = X.to_numpy(dtype=float)
        else:
            X_mat = np.asarray(X, dtype=float)

        if X_mat.shape[1] != len(self.data_min_):
            raise ValueError(
                f"Feature dimension mismatch: expected {len(self.data_min_)}, got {X_mat.shape[1]}"
            )

        # Linear mapping: target_min + (x - min) * scale
        X_scaled = self.target_min + (X_mat - self.data_min_) * self.scale_

        if self.clip:
            X_scaled = np.clip(X_scaled, self.target_min, self.target_max)

        return X_scaled

    def fit_transform(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        feature_names: Optional[List[str]] = None
    ) -> np.ndarray:
        """Fits scaler on X and returns transformed matrix."""
        return self.fit(X, feature_names=feature_names).transform(X)

    def to_dict(self) -> Dict:
        """Exports learned scaler parameters for transparency and persistence."""
        if not self.is_fitted:
            raise RuntimeError("Cannot export parameters of an unfitted scaler.")

        return {
            "target_min": self.target_min,
            "target_max": self.target_max,
            "clip": self.clip,
            "feature_names": self.feature_names,
            "data_min": self.data_min_.tolist(),
            "data_max": self.data_max_.tolist(),
            "data_range": self.data_range_.tolist(),
            "scale": self.scale_.tolist(),
        }
