"""
Market Regime Clustering Service

Uses K-means clustering on windowed price features to detect market regimes.
Includes PCA and t-SNE for dimensionality reduction and visualization.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class ClusteringService:
    """Service for clustering market regimes based on price window features"""

    def extract_features(
        self, close_series: pd.Series, window_size: int = 30
    ) -> tuple[pd.DataFrame, list[int]]:
        """
        Extract features from windowed price segments.

        Args:
            close_series: Time series of closing prices
            window_size: Size of each window in days

        Returns:
            Tuple of (features DataFrame, segment_indices list)
        """
        try:
            segments = []
            indices = []

            for start in range(0, len(close_series) - window_size, window_size):
                segment = close_series.iloc[start : start + window_size]
                if len(segment) == window_size:
                    segments.append(segment.values)
                    indices.append(start)

            if not segments:
                raise ValueError(
                    f"Not enough data for window_size={window_size}. "
                    f"Need at least {window_size + 1} data points, got {len(close_series)}."
                )

            features = []
            for seg in segments:
                stats = {
                    "mean": float(np.mean(seg)),
                    "std": float(np.std(seg)),
                    "min": float(np.min(seg)),
                    "max": float(np.max(seg)),
                    "range": float(np.max(seg) - np.min(seg)),
                    "autocorr_1": float(pd.Series(seg).autocorr(lag=1)),
                    "autocorr_5": float(pd.Series(seg).autocorr(lag=5)),
                    "slope": self._calculate_slope(seg),
                    "volatility": float(np.std(np.diff(seg))),
                    "skewness": float(pd.Series(seg).skew()),
                    "kurtosis": float(pd.Series(seg).kurtosis()),
                }
                features.append(stats)

            features_df = pd.DataFrame(features)
            return features_df, indices

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            raise

    @staticmethod
    def _calculate_slope(values: np.ndarray) -> float:
        """Calculate linear regression slope of a series."""
        try:
            x = np.arange(len(values))
            slope, _ = np.polyfit(x, values, 1)
            return float(slope)
        except Exception:
            return 0.0

    def find_optimal_k(
        self, features: pd.DataFrame, k_range: range = range(2, 10)
    ) -> dict[str, Any]:
        """
        Find optimal number of clusters using silhouette score.

        Args:
            features: Feature DataFrame
            k_range: Range of k values to test

        Returns:
            Dictionary with silhouette scores and optimal k
        """
        try:
            X = features.values
            sil_scores = []
            kmeans_models = {}

            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(X)
                score = silhouette_score(X, labels)
                sil_scores.append(score)
                kmeans_models[k] = kmeans

                logger.debug(f"k={k} | silhouette_score={score:.4f}")

            optimal_k = int(k_range[np.argmax(sil_scores)])

            return {
                "silhouette_scores": {int(k): round(float(s), 4) for k, s in zip(k_range, sil_scores, strict=False)},
                "optimal_k": optimal_k,
                "optimal_score": round(float(max(sil_scores)), 4),
            }

        except Exception as e:
            logger.error(f"Error finding optimal k: {e}")
            raise

    def cluster_data(
        self,
        features: pd.DataFrame,
        k: int | None = None,
        kmeans_model: KMeans | None = None,
    ) -> dict[str, Any]:
        """
        Perform K-means clustering on features.

        Args:
            features: Feature DataFrame
            k: Number of clusters (if None, uses best available model)
            kmeans_model: Pre-fitted KMeans model

        Returns:
            Dictionary with cluster assignments and stats
        """
        try:
            if kmeans_model is not None:
                labels = kmeans_model.predict(features.values)
            elif k is not None:
                kmeans_model = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans_model.fit_predict(features.values)
            else:
                raise ValueError("Either k or kmeans_model must be provided")

            features_with_clusters = features.copy()
            features_with_clusters["cluster"] = labels

            # Cluster statistics
            cluster_stats = {}
            for cluster_id in sorted(set(labels)):
                mask = labels == cluster_id
                cluster_stats[int(cluster_id)] = {
                    "size": int(mask.sum()),
                    "mean_features": {
                        col: round(float(features.loc[mask, col].mean()), 4)
                        for col in features.columns
                    },
                }

            return {
                "labels": labels.tolist(),
                "features": features_with_clusters,
                "cluster_stats": cluster_stats,
                "n_clusters": len(set(labels)),
            }

        except Exception as e:
            logger.error(f"Error clustering data: {e}")
            raise

    def reduce_dimensions(
        self,
        features: pd.DataFrame,
        method: str = "both",
        n_components: int = 2,
    ) -> dict[str, Any]:
        """
        Reduce feature dimensions using PCA and/or t-SNE.

        Args:
            features: Feature DataFrame (without cluster column)
            method: 'pca', 'tsne', or 'both'
            n_components: Number of output dimensions

        Returns:
            Dictionary with reduced dimensions
        """
        try:
            X = features.drop(columns=["cluster"], errors="ignore").values

            result = {}

            if method in ("pca", "both"):
                pca = PCA(n_components=n_components)
                pca_result = pca.fit_transform(X)
                result["pca"] = {
                    "data": pca_result.tolist(),
                    "explained_variance_ratio": [
                        round(float(v), 4) for v in pca.explained_variance_ratio_
                    ],
                }

            if method in ("tsne", "both"):
                perplexity = min(10, len(X) - 1)
                tsne = TSNE(
                    n_components=n_components,
                    perplexity=perplexity,
                    random_state=42,
                    max_iter=1000,
                )
                tsne_result = tsne.fit_transform(X)
                result["tsne"] = {"data": tsne_result.tolist()}

            return result

        except Exception as e:
            logger.error(f"Error reducing dimensions: {e}")
            raise

    def get_market_regimes(
        self,
        close_series: pd.Series,
        window_size: int = 30,
        k_range: range = range(2, 10),
    ) -> dict[str, Any]:
        """
        Complete market regime analysis pipeline.

        Args:
            close_series: Time series of closing prices
            window_size: Size of each window in days
            k_range: Range of k values for silhouette analysis

        Returns:
            Complete analysis with clusters, optimal k, and dimensions
        """
        try:
            # Step 1: Extract features
            features, _ = self.extract_features(close_series, window_size)

            # Step 2: Find optimal k
            optimal_info = self.find_optimal_k(features, k_range)
            optimal_k = optimal_info["optimal_k"]

            # Step 3: Cluster with optimal k
            clustering_result = self.cluster_data(features, k=optimal_k)

            # Step 4: Reduce dimensions for visualization
            dim_result = self.reduce_dimensions(
                clustering_result["features"], method="both"
            )

            return {
                "window_size": window_size,
                "n_windows": len(features),
                "optimal_k": optimal_k,
                "silhouette_score": optimal_info["optimal_score"],
                "silhouette_scores": optimal_info["silhouette_scores"],
                "cluster_stats": clustering_result["cluster_stats"],
                "n_clusters": clustering_result["n_clusters"],
                "dimensions": dim_result,
                "timestamp": pd.Timestamp.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting market regimes: {e}")
            raise


# Singleton instance
_clustering_service_instance = None


def get_clustering_service() -> ClusteringService:
    """Get or create ClusteringService singleton instance"""
    global _clustering_service_instance
    if _clustering_service_instance is None:
        _clustering_service_instance = ClusteringService()
    return _clustering_service_instance
