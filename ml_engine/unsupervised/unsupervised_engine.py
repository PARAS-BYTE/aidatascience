"""
Unsupervised Learning Engine — Clustering AutoML (K-Means, DBSCAN, Agglomerative, GMM),
Unsupervised Anomaly Detection (Isolation Forest, LOF), 2D/3D PCA Dimensionality Reduction,
Auto-K Optimization (Silhouette, Davies-Bouldin, Elbow), and Automated Segment Profiling.
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score


class UnsupervisedEngine:
    """Comprehensive, CPU-friendly unsupervised machine learning engine."""

    # ─── Data Preprocessing ───────────────────────────────────────────

    @staticmethod
    def preprocess_features(
        df: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, List[str], pd.DataFrame]:
        """Imputes and scales numerical/categorical features for distance-based ML."""
        cols = feature_columns if feature_columns else df.columns.tolist()
        sub_df = df[cols].copy()

        num_cols = sub_df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = sub_df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

        transformed_parts = []
        feature_names = []

        # 1. Numerical preprocessing
        if num_cols:
            imputer_num = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            X_num = scaler.fit_transform(imputer_num.fit_transform(sub_df[num_cols]))
            transformed_parts.append(X_num)
            feature_names.extend(num_cols)

        # 2. Categorical preprocessing
        if cat_cols:
            # Drop very high cardinality categories (> 50 unique)
            usable_cats = [c for c in cat_cols if sub_df[c].nunique() <= 50]
            if usable_cats:
                imputer_cat = SimpleImputer(strategy="most_frequent")
                cat_imputed = imputer_cat.fit_transform(sub_df[usable_cats].astype(str))
                encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                X_cat = encoder.fit_transform(cat_imputed)
                transformed_parts.append(X_cat)
                feature_names.extend(encoder.get_feature_names_out(usable_cats).tolist())

        if not transformed_parts:
            # Fallback: convert everything to numeric
            X = sub_df.apply(pd.to_numeric, errors="coerce").fillna(0).values
            feature_names = cols
        else:
            X = np.hstack(transformed_parts)

        return X, feature_names, sub_df

    # ─── 1. Clustering AutoML & Auto-K ────────────────────────────────

    @classmethod
    def run_clustering(
        cls,
        df: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
        algorithm: str = "kmeans",
        n_clusters: Optional[int] = None,
        auto_k: bool = True,
        k_min: int = 2,
        k_max: int = 8,
    ) -> Dict[str, Any]:
        """Run clustering with optional auto-K optimization and automated cluster profiling."""
        rows = len(df)
        if rows < 4:
            return {"error": "Dataset must contain at least 4 rows for clustering."}

        X, feature_names, sub_df = cls.preprocess_features(df, feature_columns)
        algorithm = algorithm.lower().strip()

        # 1. Auto-K Optimization if requested
        optimization_curve = []
        best_k = n_clusters or 3

        if auto_k and algorithm in ("kmeans", "agglomerative", "gmm"):
            max_k = min(k_max, max(rows - 1, 2))
            min_k = min(k_min, max_k)

            best_silhouette = -1.0
            for k in range(min_k, max_k + 1):
                try:
                    if algorithm == "kmeans":
                        model = KMeans(n_clusters=k, random_state=42, n_init=10)
                        labels = model.fit_predict(X)
                        inertia = float(model.inertia_)
                    elif algorithm == "gmm":
                        model = GaussianMixture(n_components=k, random_state=42)
                        labels = model.fit_predict(X)
                        inertia = None
                    else:
                        model = AgglomerativeClustering(n_clusters=k)
                        labels = model.fit_predict(X)
                        inertia = None

                    # Verify at least 2 distinct clusters were produced
                    if len(set(labels)) > 1:
                        sil = float(silhouette_score(X, labels))
                        db = float(davies_bouldin_score(X, labels))
                        ch = float(calinski_harabasz_score(X, labels))

                        optimization_curve.append({
                            "k": k,
                            "silhouette_score": round(sil, 4),
                            "davies_bouldin_index": round(db, 4),
                            "calinski_harabasz": round(ch, 2),
                            "inertia": round(inertia, 2) if inertia is not None else None,
                        })

                        if sil > best_silhouette:
                            best_silhouette = sil
                            best_k = k
                except Exception:
                    continue

        # 2. Fit Final Model
        if algorithm == "dbscan":
            model = DBSCAN(eps=0.5, min_samples=5)
            cluster_labels = model.fit_predict(X)
            unique_labels = set(cluster_labels)
            actual_k = len(unique_labels - {-1})
        elif algorithm == "gmm":
            model = GaussianMixture(n_components=best_k, random_state=42)
            cluster_labels = model.fit_predict(X)
            actual_k = best_k
        elif algorithm == "agglomerative":
            model = AgglomerativeClustering(n_clusters=best_k)
            cluster_labels = model.fit_predict(X)
            actual_k = best_k
        else:
            model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            cluster_labels = model.fit_predict(X)
            actual_k = best_k

        # 3. Compute Final Evaluation Metrics
        valid_labels = set(cluster_labels)
        if len(valid_labels) > 1 and not (len(valid_labels) == 2 and -1 in valid_labels):
            final_sil = round(float(silhouette_score(X, cluster_labels)), 4)
            final_db = round(float(davies_bouldin_score(X, cluster_labels)), 4)
            final_ch = round(float(calinski_harabasz_score(X, cluster_labels)), 2)
        else:
            final_sil, final_db, final_ch = 0.0, 0.0, 0.0

        # 4. 2D PCA Projection for visualization
        pca_2d = PCA(n_components=2, random_state=42)
        coords = pca_2d.fit_transform(X)
        exp_var = [round(float(v) * 100, 2) for v in pca_2d.explained_variance_ratio_]

        # Downsample points for fast UI rendering if > 1500
        step = max(1, len(coords) // 1500)
        sample_indices = list(range(0, len(coords), step))

        scatter_points = []
        for idx in sample_indices:
            scatter_points.append({
                "x": round(float(coords[idx, 0]), 3),
                "y": round(float(coords[idx, 1]), 3),
                "cluster": int(cluster_labels[idx]),
                "row_index": idx,
            })

        # 5. Cluster Personas & Distinctive Profiles
        personas = cls._generate_cluster_personas(sub_df, cluster_labels)

        return {
            "algorithm": algorithm,
            "optimal_k": actual_k,
            "metrics": {
                "silhouette_score": final_sil,
                "davies_bouldin_index": final_db,
                "calinski_harabasz": final_ch,
                "cluster_separation_rating": "Strong" if final_sil >= 0.5 else ("Moderate" if final_sil >= 0.25 else "Weak/Overlapping"),
            },
            "cluster_distribution": {
                str(c): int((cluster_labels == c).sum())
                for c in sorted(list(set(cluster_labels)))
            },
            "optimization_curve": optimization_curve,
            "pca_projection": {
                "explained_variance_pct": exp_var,
                "total_variance_explained": round(sum(exp_var), 2),
                "points": scatter_points,
            },
            "cluster_personas": personas,
            "cluster_labels": [int(l) for l in cluster_labels],
        }

    # ─── Cluster Personas Generator ───────────────────────────────────

    @staticmethod
    def _generate_cluster_personas(
        df: pd.DataFrame,
        labels: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Generate human-understandable persona profiles for each cluster."""
        total_rows = len(df)
        unique_labels = sorted([l for l in set(labels) if l != -1])
        personas = []

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        overall_means = df[num_cols].mean().to_dict() if num_cols else {}

        for cluster_id in unique_labels:
            mask = (labels == cluster_id)
            c_count = int(mask.sum())
            c_pct = round((c_count / total_rows) * 100, 1)

            cluster_subset = df[mask]

            distinctive_traits = []
            feature_stats = {}

            if num_cols:
                for col in num_cols:
                    c_mean = float(cluster_subset[col].mean())
                    all_mean = float(overall_means.get(col, 0.0))
                    feature_stats[col] = {
                        "cluster_mean": round(c_mean, 2),
                        "overall_mean": round(all_mean, 2),
                    }

                    if all_mean != 0:
                        diff_pct = ((c_mean - all_mean) / abs(all_mean)) * 100
                        if abs(diff_pct) >= 25.0:
                            direction = "higher" if diff_pct > 0 else "lower"
                            distinctive_traits.append({
                                "feature": col,
                                "diff_pct": round(diff_pct, 1),
                                "description": f"{abs(round(diff_pct, 1))}% {direction} than population average",
                            })

            # Sort traits by absolute deviation
            distinctive_traits = sorted(distinctive_traits, key=lambda x: abs(x["diff_pct"]), reverse=True)[:3]

            # Generate persona title
            if distinctive_traits:
                top_trait = distinctive_traits[0]
                sign = "High" if top_trait["diff_pct"] > 0 else "Low"
                persona_title = f"{sign} {top_trait['feature']} Segment"
                persona_summary = f"Characterized by {top_trait['feature']} ({top_trait['description']}). Represents {c_pct}% of population."
            else:
                persona_title = f"Core Average Cluster {cluster_id}"
                persona_summary = f"Represents balanced population baseline characteristics across all evaluated features ({c_pct}%)."

            personas.append({
                "cluster_id": int(cluster_id),
                "title": persona_title,
                "summary": persona_summary,
                "count": c_count,
                "percentage": c_pct,
                "distinctive_traits": distinctive_traits,
                "feature_stats": feature_stats,
            })

        return personas

    # ─── 2. Unsupervised Anomaly Detection ────────────────────────────

    @classmethod
    def detect_anomalies(
        cls,
        df: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
        algorithm: str = "isolation_forest",
        contamination: float = 0.05,
    ) -> Dict[str, Any]:
        """Detect unlabeled anomalies using Isolation Forest or Local Outlier Factor."""
        rows = len(df)
        if rows < 10:
            return {"error": "Dataset must contain at least 10 rows for anomaly detection."}

        X, feature_names, sub_df = cls.preprocess_features(df, feature_columns)

        contamination = max(0.01, min(0.30, contamination))

        if algorithm.lower() == "lof":
            model = LocalOutlierFactor(n_neighbors=min(20, rows - 1), contamination=contamination)
            preds = model.fit_predict(X)  # -1 = anomaly, 1 = normal
            scores = -model.negative_outlier_factor_  # Higher = more anomalous
        else:
            model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
            preds = model.fit_predict(X)  # -1 = anomaly, 1 = normal
            scores = -model.decision_function(X)  # Higher = more anomalous

        is_anomaly = (preds == -1)
        anomaly_count = int(is_anomaly.sum())
        anomaly_pct = round((anomaly_count / rows) * 100, 2)

        # 2D PCA for visual anomaly inspection
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(X)

        step = max(1, len(coords) // 1500)
        sample_indices = list(range(0, len(coords), step))

        points = []
        for idx in sample_indices:
            points.append({
                "x": round(float(coords[idx, 0]), 3),
                "y": round(float(coords[idx, 1]), 3),
                "is_anomaly": bool(is_anomaly[idx]),
                "score": round(float(scores[idx]), 3),
                "row_index": idx,
            })

        # Identify top anomalous records
        top_anomaly_indices = np.argsort(scores)[::-1][:10]
        top_records = []
        for idx in top_anomaly_indices:
            if is_anomaly[idx]:
                top_records.append({
                    "row_index": int(idx),
                    "anomaly_score": round(float(scores[idx]), 4),
                    "data": {col: str(sub_df.iloc[idx][col]) for col in sub_df.columns[:8]},
                })

        return {
            "algorithm": algorithm,
            "contamination_rate": contamination,
            "total_rows": rows,
            "anomaly_count": anomaly_count,
            "anomaly_percentage": anomaly_pct,
            "status": "Anomalies Identified" if anomaly_count > 0 else "Clean Dataset",
            "pca_projection": {
                "explained_variance": [round(float(v) * 100, 2) for v in pca.explained_variance_ratio_],
                "points": points,
            },
            "top_anomalies": top_records,
            "anomaly_flags": [int(1 if a else 0) for a in is_anomaly],
        }

    # ─── 3. Dimensionality Reduction (PCA) ────────────────────────────

    @classmethod
    def run_pca(
        cls,
        df: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
        n_components: int = 2,
    ) -> Dict[str, Any]:
        """Compute PCA decomposition, explained variance, and feature loadings."""
        X, feature_names, sub_df = cls.preprocess_features(df, feature_columns)
        n_components = max(2, min(n_components, X.shape[1], X.shape[0]))

        pca = PCA(n_components=n_components, random_state=42)
        coords = pca.fit_transform(X)

        exp_var = [round(float(v) * 100, 2) for v in pca.explained_variance_ratio_]
        cum_var = [round(float(v) * 100, 2) for v in np.cumsum(pca.explained_variance_ratio_)]

        # Feature Loadings (components_ has shape [n_components, n_features])
        loadings = {}
        for comp_idx in range(min(n_components, 3)):
            comp_name = f"PC{comp_idx + 1}"
            raw_loadings = pca.components_[comp_idx]
            # Match top features
            sorted_indices = np.argsort(np.abs(raw_loadings))[::-1][:6]
            loadings[comp_name] = [
                {
                    "feature": feature_names[i] if i < len(feature_names) else f"Feature_{i}",
                    "loading": round(float(raw_loadings[i]), 4),
                    "impact": "Positive" if raw_loadings[i] > 0 else "Negative",
                }
                for i in sorted_indices
            ]

        step = max(1, len(coords) // 1500)
        sample_indices = list(range(0, len(coords), step))

        points = [
            {
                "pc1": round(float(coords[i, 0]), 3),
                "pc2": round(float(coords[i, 1]), 3),
                "pc3": round(float(coords[i, 2]), 3) if n_components >= 3 else None,
                "row_index": i,
            }
            for i in sample_indices
        ]

        return {
            "n_components": n_components,
            "explained_variance_pct": exp_var,
            "cumulative_variance_pct": cum_var,
            "total_variance_explained": cum_var[-1] if cum_var else 0.0,
            "feature_loadings": loadings,
            "points": points,
        }
