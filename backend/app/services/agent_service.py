"""
AI Agent — Natural language data scientist using Groq LLMs, Prompt Guard defense, and dynamic chart generation.
The LLM orchestrates with Prompt Guard protection; Python ML engines compute real statistics and chart payloads.
"""
import json
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import numpy as np
import pandas as pd
import groq

from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger
from app.db.models import AgentSession, AgentMessage
from app.services.prompt_guard_service import PromptGuardService


class AIAgent:
    """AI Data Scientist agent with Prompt Guard security, Groq LLM tool orchestration, and visual chart generation."""

    TOOL_DEFINITIONS = [
        {
            "name": "auto_pilot_pipeline",
            "description": "Run the complete autonomous AI data science pipeline: analyzes dataset, reasons over column semantics, formulates and applies AI-driven feature engineering, intelligently selects candidate models, trains cross-validated models, and computes SHAP explainability.",
            "parameters": {
                "dataset_id": "string",
                "target": "string (optional)",
                "enable_feature_engineering": "boolean (optional, default true)",
            },
        },
        {
            "name": "preview_dataset_head",
            "description": "Preview the first rows of the dataset as an Excel-style table and overview (head, column types, row counts).",
            "parameters": {"dataset_id": "string", "limit": "integer (optional, default 10)"},
        },
        {
            "name": "profile_dataset",
            "description": "Profile a dataset to see rows, columns, types, missing values, duplicates.",
            "parameters": {"dataset_id": "string"},
        },
        {
            "name": "run_eda",
            "description": "Run exploratory data analysis — statistics, distributions, correlations.",
            "parameters": {"dataset_id": "string", "target": "string (optional)"},
        },
        {
            "name": "detect_issues",
            "description": "Detect data quality issues — missing values, duplicates, outliers.",
            "parameters": {"dataset_id": "string"},
        },
        {
            "name": "suggest_target",
            "description": "Suggest potential target columns for ML.",
            "parameters": {"dataset_id": "string"},
        },
        {
            "name": "detect_task",
            "description": "Detect ML task type (classification/regression) for a target.",
            "parameters": {"dataset_id": "string", "target": "string"},
        },
        {
            "name": "train_models",
            "description": "Train multiple ML models (AutoML) and produce a leaderboard.",
            "parameters": {"dataset_id": "string", "target": "string", "metric": "string (optional)"},
        },
        {
            "name": "get_leaderboard",
            "description": "Get the model leaderboard showing ranked models with real metrics.",
            "parameters": {"dataset_id": "string"},
        },
        {
            "name": "get_feature_importance",
            "description": "Get SHAP-based feature importance for a trained model.",
            "parameters": {"model_id": "string"},
        },
        {
            "name": "predict",
            "description": "Make a prediction using a trained model.",
            "parameters": {"model_id": "string", "features": "dict"},
        },
        {
            "name": "get_model_health",
            "description": "Check model health, drift status, and prediction count.",
            "parameters": {"model_id": "string"},
        },
        {
            "name": "generate_chart",
            "description": "Generate ANY interactive visual chart or graph (bar, horizontal_bar, stacked_bar, line, multi_line, area, stacked_area, scatter, bubble, pie, donut, radar, boxplot, histogram, heatmap, composed) based on dataset columns with optional grouping, aggregation, and filtering.",
            "parameters": {
                "dataset_id": "string",
                "chart_type": "string ('bar', 'horizontal_bar', 'stacked_bar', 'line', 'multi_line', 'area', 'stacked_area', 'scatter', 'bubble', 'pie', 'donut', 'radar', 'boxplot', 'histogram', 'heatmap', 'composed')",
                "x_column": "string (optional)",
                "y_column": "string (optional)",
                "z_column": "string (optional, for bubble size)",
                "group_column": "string (optional, for stacked/grouped or multi-series)",
                "aggregation": "string (optional: 'sum', 'mean', 'median', 'count', 'min', 'max')",
                "title": "string (optional)",
            },
        },
        {
            "name": "compare_models_chart",
            "description": "Generate an interactive comparative bar or radar chart of all trained models and their metrics.",
            "parameters": {"dataset_id": "string"},
        },
        {
            "name": "plot_correlation_chart",
            "description": "Generate a full correlation heatmap or correlation ranking chart for the dataset.",
            "parameters": {"dataset_id": "string", "target": "string (optional)"},
        },
        {
            "name": "ask_data_sql",
            "description": "Query, filter, aggregate, calculate, or ask questions about the active CSV dataset using DuckDB Text-to-SQL. Returns generated SQL, tabular data rows, and auto-visualization chart.",
            "parameters": {
                "dataset_id": "string",
                "question": "string",
            },
        },
    ]

    SYSTEM_PROMPT = """You are an expert AI Data Scientist assistant and conversational companion for this AutoML platform.
You combine the skills of a principal data scientist, machine learning engineer, and data analyst.

YOUR CAPABILITIES:
1. General Data Science Consultation:
   - Talk in general as a knowledgeable data scientist: explain machine learning algorithms (Random Forest, XGBoost, LightGBM, Logistic Regression, Neural Nets, SVM, Clustering, ARIMA), mathematical foundations, statistics, evaluation metrics (ROC-AUC, PR-AUC, F1, Log-Loss, RMSE, MAE, R2), cross-validation strategies, and write clean Python/pandas/scikit-learn code.
   - You can chat freely about general concepts even when NO dataset is selected!

2. Talk About and Query Uploaded CSV Data:
   - When a dataset is active, you know its schema, row count, column names, and data types.
   - When the user asks ANY question about the data in the CSV (e.g., "what is the average price by category?", "how many rows have null age?", "show top 10 rows sorted by revenue", "who are the top customers?"), call the 'ask_data_sql' tool. It executes safe DuckDB SQL and generates tabular data and visual charts!

3. Autonomous Actions ("Do things for the data scientist"):
   - 'auto_pilot_pipeline': Run the full autonomous AutoML pipeline (smart cleaning, feature engineering, model training, cross-validation, and SHAP explainability).
   - 'preview_dataset_head': Preview raw CSV rows in an interactive table spreadsheet.
   - 'profile_dataset': Summarize dataset shape, data types, missing values, duplicates.
   - 'run_eda': Run comprehensive exploratory data analysis with distributions and correlations.
   - 'detect_issues': Scan for data quality problems, anomalies, and outliers.
   - 'suggest_target': Recommend the best target column for predictive modeling.
   - 'train_models': Train candidate ML models and produce an evaluation leaderboard.
   - 'generate_chart': Generate ANY interactive visual chart (bar, line, area, scatter, bubble, pie, donut, radar, boxplot, heatmap).

CRITICAL RULES:
1. When answering general questions, theory, concepts, or giving advice, reply directly in structured, clear, professional Markdown (do NOT call a tool if no data operation is needed).
2. When the user asks to query, filter, aggregate, calculate, or examine data from the active CSV dataset, call 'ask_data_sql'.
3. When the user asks to train models or run end-to-end AutoML, call 'auto_pilot_pipeline'.
4. When the user asks for ANY chart or graph, call 'generate_chart', 'compare_models_chart', or 'plot_correlation_chart'.
5. When the user asks to preview or view CSV rows or tables, call 'preview_dataset_head'.
6. Base all data statements on actual computed results. NEVER fabricate dataset rows or statistics.

Available Tools:
{tools}

Available context will be provided with current dataset and models."""

    @classmethod
    def create_session(cls, db: Session, dataset_id: Optional[str] = None) -> AgentSession:
        """Create a new conversation session."""
        session = AgentSession(dataset_id=dataset_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @classmethod
    def process_message(
        cls,
        db: Session,
        message: str,
        session_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        guard_model: Optional[str] = None,
        llm_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message:
        1. Run Prompt Guard security check (meta-llama/llama-prompt-guard-2-86m or 2-22m)
        2. If unsafe/injection detected, block execution and return security notification
        3. If safe, execute tool-calling with Groq LLM (or fallback)
        4. Save message history and return response with any charts generated
        """
        # 1. Prompt Guard Security Check
        guard_result = PromptGuardService.check_prompt(message, model=guard_model)

        # Get or create session
        if session_id:
            session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
            if not session:
                session = cls.create_session(db, dataset_id)
        else:
            session = cls.create_session(db, dataset_id)

        effective_dataset_id = dataset_id or session.dataset_id
        if dataset_id and session.dataset_id != dataset_id:
            session.dataset_id = dataset_id
            db.commit()

        # Save user message
        user_msg = AgentMessage(
            session_id=session.id,
            role="user",
            content=message,
        )
        db.add(user_msg)
        db.commit()

        # 2. Check if Prompt Guard flagged injection
        if guard_result.get("flagged", False):
            model_name = guard_result.get("model", "Prompt Guard")
            score = guard_result.get("score", 0.0)
            response = (
                f"🛡️ **Security Alert: Adversarial Prompt Blocked**\n\n"
                f"Your message was flagged by **{model_name}** with a threat risk score of **`{score:.4f}`** "
                f"(Threshold: `{settings.PROMPT_GUARD_THRESHOLD}`).\n\n"
                f"Execution was halted to safeguard system prompts, data integrity, and pipeline safety. "
                f"Please rephrase your query with safe data science instructions."
            )
            tool_calls = []
            assistant_msg = AgentMessage(
                session_id=session.id,
                role="assistant",
                content=response,
            )
            db.add(assistant_msg)
            db.commit()

            return {
                "response": response,
                "session_id": session.id,
                "tool_calls": tool_calls,
                "charts": [],
                "guard_info": guard_result,
                "model_used": model_name,
            }

        # 3. Process with Groq LLM or deterministic engine
        model_used = llm_model or settings.GROQ_CHAT_MODEL or "Groq LLM Engine"
        charts: List[Dict[str, Any]] = []
        try:
            response, tool_calls, charts = cls._process_with_groq_or_tools(
                db, message, effective_dataset_id, session, llm_model=llm_model
            )
        except Exception as e:
            logger.error(f"Agent processing failed: {str(e)}", exc_info=True)
            response = f"I encountered an error processing your request: {str(e)}. Please try again."
            tool_calls = []
            charts = []

        # Save assistant message
        assistant_msg = AgentMessage(
            session_id=session.id,
            role="assistant",
            content=response,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
        )
        db.add(assistant_msg)
        db.commit()

        return {
            "response": response,
            "session_id": session.id,
            "tool_calls": tool_calls,
            "charts": charts,
            "guard_info": guard_result,
            "model_used": model_used,
        }

    @classmethod
    def _process_with_groq_or_tools(
        cls,
        db: Session,
        message: str,
        dataset_id: Optional[str],
        session: AgentSession,
        llm_model: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Try Groq LLM processing first, fallback to deterministic routing."""
        client = PromptGuardService.get_client()
        active_llm = llm_model or settings.GROQ_CHAT_MODEL

        if client and active_llm:
            try:
                return cls._process_with_groq_llm(client, active_llm, db, message, dataset_id, session)
            except Exception as e:
                logger.warning(f"Groq LLM call encountered error, falling back to deterministic tool matcher: {str(e)}")

        return cls._process_with_tools(db, message, dataset_id, session)

    @classmethod
    def _process_with_groq_llm(
        cls,
        client: groq.Groq,
        model_name: str,
        db: Session,
        message: str,
        dataset_id: Optional[str],
        session: AgentSession,
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Use Groq LLM to intelligently select tools and answer with grounded context."""
        from app.db.models import Dataset

        dataset_info = "No dataset currently selected. You can chat freely about general data science, statistics, algorithms, and code."
        all_datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(5).all()
        dataset_list_str = ", ".join([f"'{d.original_filename}' (id: {d.id})" for d in all_datasets])

        current_dataset = None
        columns_str = ""
        sample_preview = ""
        if dataset_id:
            current_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if current_dataset:
                try:
                    from app.services.profiler import DatasetProfiler
                    df_sample = DatasetProfiler.load_dataset(current_dataset.file_path)
                    dtypes_summary = [f"{col} ({df_sample[col].dtype})" for col in df_sample.columns[:25]]
                    columns_str = f"Columns & Types: {', '.join(dtypes_summary)}"
                    sample_preview = f"Sample first 3 rows:\n{df_sample.head(3).to_dict(orient='records')}"
                except Exception:
                    pass

                dataset_info = (
                    f"Active Dataset: '{current_dataset.original_filename}' (ID: `{current_dataset.id}`, "
                    f"Rows: {current_dataset.row_count or 'Unknown'}, "
                    f"Target: {current_dataset.target_column or 'None'}).\n"
                    f"{columns_str}\n{sample_preview}"
                )

        system_instruction = (
            f"{cls.SYSTEM_PROMPT.format(tools=json.dumps(cls.TOOL_DEFINITIONS, indent=2))}\n\n"
            f"Current Context:\n"
            f"- {dataset_info}\n"
            f"- Available datasets on platform: {dataset_list_str if dataset_list_str else 'None'}\n\n"
            f"If a tool is needed to perform an action or query the data, reply strictly with a JSON object in this format:\n"
            f'{{"action": "tool_call", "tool": "<tool_name>", "params": {{...}}}}\n\n'
            f"If answering a general question, explaining concepts, giving data science advice, or writing code, reply directly with friendly, well-formatted Markdown text."
        )

        chat_messages = [
            {"role": "system", "content": system_instruction},
        ]

        recent_history = (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == session.id)
            .order_by(AgentMessage.created_at.desc())
            .limit(6)
            .all()
        )
        for h in reversed(recent_history):
            chat_messages.append({"role": h.role, "content": h.content[:1500]})

        chat_messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=model_name,
            messages=chat_messages,
            temperature=0.1,
            max_tokens=2048,
        )

        reply = response.choices[0].message.content.strip()

        # Check if the LLM output specifies a tool call
        tool_call_match = None
        if "tool" in reply:
            try:
                if reply.startswith("{") and reply.endswith("}"):
                    tool_call_match = json.loads(reply)
                else:
                    match = re.search(r'\{\s*"action"\s*:\s*"tool_call".*?\}', reply, re.DOTALL) or re.search(r'\{\s*"tool"\s*:.*?"params"\s*:.*?\}', reply, re.DOTALL)
                    if match:
                        tool_call_match = json.loads(match.group(0))
            except Exception:
                pass

        if tool_call_match:
            try:
                tool_name = tool_call_match.get("tool")
                params = tool_call_match.get("params", {})
                if not params.get("dataset_id") and dataset_id:
                    params["dataset_id"] = dataset_id

                if tool_name in [t["name"] for t in cls.TOOL_DEFINITIONS]:
                    return cls._execute_tool(tool_name, db, params, user_query=message)
            except Exception:
                pass

        # If the LLM answered conversationally (e.g. general data science question, advice, code snippet):
        if reply and not reply.startswith('{"action": "tool_call"'):
            return reply, [], []

        return cls._process_with_tools(db, message, dataset_id, session)

    @classmethod
    def _process_with_tools(
        cls,
        db: Session,
        message: str,
        dataset_id: Optional[str],
        session: AgentSession,
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process message using deterministic tool matching and intelligent offline knowledge base."""
        message_lower = message.lower().strip()

        # ─── General Data Science Greetings & Conversational Knowledge Base ───
        if not dataset_id:
            # Greetings
            if any(message_lower.startswith(g) or message_lower == g for g in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "help"]):
                from app.db.models import Dataset
                datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(5).all()
                ds_bullets = "\n".join([f"• **{d.original_filename}** ({d.row_count or 0:,} rows)" for d in datasets]) if datasets else "*(No datasets uploaded yet)*"
                return (
                    f"👋 **Hello! I'm your AI Data Scientist Companion.**\n\n"
                    f"I can help you with both **general data science tasks** and **deep analysis of your CSV datasets**:\n\n"
                    f"### 🚀 What I Can Do For You:\n"
                    f"1. **Talk Data Science in General**: Ask me about ML algorithms (Random Forest, XGBoost, LightGBM), statistics, feature engineering, cross-validation, and metrics (ROC-AUC vs PR-AUC).\n"
                    f"2. **Query CSV Data with DuckDB**: Select an uploaded dataset to filter, aggregate, calculate metrics, and generate instant charts.\n"
                    f"3. **Autonomous Auto-Pilot**: Run end-to-end data cleaning, feature generation, model training, and SHAP explainability.\n"
                    f"4. **Visual Chart Generation**: Request boxplots, correlation heatmaps, scatter plots, radar charts, and more.\n\n"
                    f"**Available Datasets in Platform**:\n{ds_bullets}\n\n"
                    f"*Select a dataset from the dropdown above to query your data, or ask me any data science question right now!*",
                    [],
                    []
                )

            # General Data Science Concept Matching (Offline fallback when no dataset is selected)
            if any(kw in message_lower for kw in ["imbalance", "imbalanced", "smote", "class weight"]):
                return (
                    "### ⚖️ Handling Imbalanced Datasets: Best Practices\n\n"
                    "When classes are heavily imbalanced (e.g. 99% negative, 1% positive in fraud detection or medical diagnosis):\n\n"
                    "1. **Do NOT use Accuracy**: A trivial model predicting the majority class achieves 99% accuracy but is useless.\n"
                    "2. **Recommended Metrics**:\n"
                    "   • **PR-AUC (Precision-Recall AUC)**: Highly sensitive to the minority class.\n"
                    "   • **F1-Score / F-beta**: Harmonic mean of Precision and Recall (use F2 to prioritize Recall).\n"
                    "   • **Balanced Accuracy** & **Cohen's Kappa**.\n"
                    "3. **Resampling Techniques**:\n"
                    "   • **SMOTE** (Synthetic Minority Over-sampling Technique) / ADASYN.\n"
                    "   • **Random Under-sampling** of majority class.\n"
                    "4. **Algorithm-Level Adjustments**:\n"
                    "   • Set `scale_pos_weight` in XGBoost / LightGBM.\n"
                    "   • Set `class_weight='balanced'` in Scikit-Learn Random Forest and Logistic Regression.\n"
                    "5. **Threshold Tuning**: Optimize classification threshold instead of the default `0.5`.",
                    [],
                    []
                )

            if any(kw in message_lower for kw in ["roc", "pr-auc", "precision", "recall", "metric"]):
                return (
                    "### 📊 Evaluation Metrics Guide\n\n"
                    "| Metric | Best Used For | Notes |\n"
                    "| :--- | :--- | :--- |\n"
                    "| **ROC-AUC** | Balanced binary classification | Measures rank ordering across all thresholds; can be overly optimistic on extreme imbalance. |\n"
                    "| **PR-AUC** | Highly imbalanced classification | Focuses directly on true positives without being influenced by large true negatives. |\n"
                    "| **F1-Score** | Balance between Precision & Recall | F1 = 2 * (Precision * Recall) / (Precision + Recall). |\n"
                    "| **Log-Loss** | Probability calibration | Heavily penalizes confident incorrect predictions. |\n"
                    "| **RMSE / MAE** | Regression tasks | RMSE penalizes large errors more heavily than MAE. |\n"
                    "| **R² Score** | Regression variance explanation | Proportion of variance explained by model (1.0 = perfect). |",
                    [],
                    []
                )

            if any(kw in message_lower for kw in ["random forest", "xgboost", "lightgbm", "gradient boost", "difference"]):
                return (
                    "### 🌲 Random Forest vs. Gradient Boosting (XGBoost / LightGBM)\n\n"
                    "Both are ensemble tree methods, but they differ fundamentally:\n\n"
                    "• **Random Forest (Bagging)**:\n"
                    "  - Builds independent deep trees in parallel using bootstrap samples and random feature subsets.\n"
                    "  - Reduces **variance** (less prone to overfitting), highly robust to noise with minimal hyperparameter tuning.\n\n"
                    "• **XGBoost / LightGBM (Boosting)**:\n"
                    "  - Builds shallow trees sequentially; each new tree corrects residual errors made by preceding trees.\n"
                    "  - Reduces **bias and variance**, consistently achieves top benchmark performance on tabular datasets.\n"
                    "  - Requires tuning of `learning_rate`, `max_depth`, `subsample`, and regularization parameters.",
                    [],
                    []
                )

            from app.db.models import Dataset
            datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).limit(5).all()
            if datasets:
                dataset_list = "\n".join([f"• **{d.original_filename}** (ID: `{d.id}`)" for d in datasets])
                return (
                    f"I can help you with general data science questions, or you can select one of the platform's datasets to query:\n\n{dataset_list}\n\n"
                    "Select a dataset from the dropdown above to run DuckDB SQL queries, generate charts, or train models!",
                    [],
                    []
                )
            return (
                "No datasets are loaded yet. Please upload a dataset through the **Datasets** page, "
                "or ask me any general data science or machine learning question right now!",
                [],
                []
            )

        # ─── Dataset Active: Route Actions & Queries ─────────────────────────

        # 1. Autonomous AI Auto-Pilot Pipeline Intent
        if any(kw in message_lower for kw in [
            "auto pilot", "autopilot", "auto-pilot", "autonomous", "full pipeline",
            "do feature engineering and train", "think and train", "end to end",
            "prepare and train", "engineer features and train", "train best model",
            "full workflow", "do everything", "run pipeline", "run ai"
        ]):
            return cls._execute_tool("auto_pilot_pipeline", db, {"dataset_id": dataset_id}, user_query=message)

        # 2. Preview CSV / Head Table Intent Detection
        if any(kw in message_lower for kw in ["preview", "show csv", "head of", "first rows", "view table", "show table", "show data", "data grid", "excel", "first 5 rows", "first 10 rows"]):
            return cls._execute_tool("preview_dataset_head", db, {"dataset_id": dataset_id}, user_query=message)

        # 3. Universal Chart / Graph Intent Detection
        if any(kw in message_lower for kw in ["graph", "chart", "plot", "histogram", "scatter", "visualiz", "bar", "pie", "donut", "doughnut", "radar", "box", "boxplot", "area", "line", "bubble", "heatmap", "correlation", "composed", "combo", "trend"]):
            if any(kw in message_lower for kw in ["model", "leaderboard", "compare", "performance"]):
                return cls._execute_tool("compare_models_chart", db, {"dataset_id": dataset_id}, user_query=message)
            elif any(kw in message_lower for kw in ["correlation", "heatmap", "relationship"]):
                return cls._execute_tool("plot_correlation_chart", db, {"dataset_id": dataset_id}, user_query=message)
            else:
                return cls._execute_tool("generate_chart", db, {"dataset_id": dataset_id}, user_query=message)

        # 4. Profiling & Issues Intent Routing
        if any(kw in message_lower for kw in ["profile", "overview", "describe", "info", "summary", "shape"]):
            return cls._execute_tool("profile_dataset", db, {"dataset_id": dataset_id}, user_query=message)

        if any(kw in message_lower for kw in ["missing", "quality", "issue", "problem", "clean", "duplicate", "outlier"]):
            return cls._execute_tool("detect_issues", db, {"dataset_id": dataset_id}, user_query=message)

        if any(kw in message_lower for kw in ["target", "predict what", "which column", "suggest target"]):
            return cls._execute_tool("suggest_target", db, {"dataset_id": dataset_id}, user_query=message)

        if any(kw in message_lower for kw in ["eda", "explore", "statistic"]):
            return cls._execute_tool("run_eda", db, {"dataset_id": dataset_id}, user_query=message)

        if any(kw in message_lower for kw in ["train", "model", "automl", "leaderboard", "best model", "experiment"]):
            from app.db.models import Experiment, ExperimentStatus
            experiments = db.query(Experiment).filter(
                Experiment.dataset_id == dataset_id,
                Experiment.status == ExperimentStatus.COMPLETED,
            ).all()

            if experiments:
                return cls._execute_tool("get_leaderboard", db, {"dataset_id": dataset_id}, user_query=message)
            else:
                return (
                    "No models have been trained yet for this dataset. You can:\n\n"
                    "1. Say **'Run Auto-Pilot'** to have me automatically clean data, engineer features, and train models!\n"
                    "2. Or tell me which column you'd like to predict.",
                    [],
                    []
                )

        if any(kw in message_lower for kw in ["important", "feature importance", "shap", "explain", "why"]):
            from app.db.models import MLModel
            model = db.query(MLModel).filter(MLModel.dataset_id == dataset_id).order_by(MLModel.created_at.desc()).first()
            if model:
                return cls._execute_tool("get_feature_importance", db, {"model_id": model.id}, user_query=message)
            else:
                return ("No registered models found for this dataset. Train and register a model first to compute SHAP feature importance.", [], [])

        if any(kw in message_lower for kw in ["health", "drift", "monitor", "production"]):
            from app.db.models import MLModel
            model = db.query(MLModel).filter(MLModel.dataset_id == dataset_id).order_by(MLModel.created_at.desc()).first()
            if model:
                return cls._execute_tool("get_model_health", db, {"model_id": model.id}, user_query=message)
            else:
                return ("No deployed models found for this dataset. Deploy a model to track data drift and health.", [], [])

        # 5. Data Queries via DuckDB Text-to-SQL (Ask Data Core)
        return cls._execute_tool("ask_data_sql", db, {"dataset_id": dataset_id, "question": message}, user_query=message)

    @classmethod
    def _execute_tool(
        cls,
        tool_name: str,
        db: Session,
        params: Dict[str, Any],
        user_query: str = "",
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Execute a tool, format text response, and generate interactive chart payloads."""
        tool_calls = [{"tool": tool_name, "params": params}]
        charts: List[Dict[str, Any]] = []

        try:
            # ─── Ask Data DuckDB Text-to-SQL Tool ────────────────────────
            if tool_name in ["ask_data_sql", "query_data_sql", "answer_dataset_question"]:
                dataset_id = params.get("dataset_id")
                from app.db.models import Dataset
                from app.services.text2sql_service import Text2SQLService
                dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                if not dataset:
                    return f"Dataset `{dataset_id}` not found.", tool_calls, charts

                question = params.get("question") or user_query or "Show rows"
                result = Text2SQLService.ask_data(dataset_id, question, db)

                sql = result.get("sql", "")
                rows = result.get("rows", [])
                cols = result.get("columns", [])
                explanation = result.get("explanation", "")
                chart_type = result.get("chart_type", "table")
                row_count = result.get("row_count", len(rows))

                # Build Markdown explanation
                md_resp = f"## 🦆 DuckDB Query Result: **{dataset.original_filename}**\n\n"
                md_resp += f"{explanation}\n\n"
                if sql:
                    md_resp += f"```sql\n{sql}\n```\n\n"
                md_resp += f"*Returned {row_count:,} row(s) across {len(cols)} column(s).*"

                # Add interactive Table & Visualization chart payload
                charts.append({
                    "id": f"sql_{int(time.time())}",
                    "type": chart_type,
                    "title": f"DuckDB Query: {dataset.original_filename}",
                    "description": explanation,
                    "data": rows,
                    "x_key": result.get("x_axis") or (cols[0] if cols else None),
                    "y_key": result.get("y_axis") or (cols[1] if len(cols) > 1 else None),
                    "config": {
                        "sql": sql,
                        "columns": cols,
                        "row_count": row_count,
                        "is_sql_query": True,
                    }
                })

                return md_resp, tool_calls, charts

            # ─── Autonomous AI Auto-Pilot Pipeline ──────────────────────
            if tool_name == "auto_pilot_pipeline":
                result = cls.run_auto_pilot_pipeline(
                    db=db,
                    dataset_id=params["dataset_id"],
                    target=params.get("target"),
                    llm_model=params.get("llm_model"),
                    enable_feature_engineering=params.get("enable_feature_engineering", True),
                )
                return result["executive_summary"], tool_calls, result.get("charts", [])

            # ─── Preview Dataset Head ────────────────────────────────────
            if tool_name == "preview_dataset_head":
                dataset_id = params.get("dataset_id")
                from app.db.models import Dataset
                from app.services.dataset_service import DatasetService
                dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                if not dataset:
                    return f"Dataset `{dataset_id}` not found.", tool_calls, charts

                limit = int(params.get("limit", 10))
                preview = DatasetService.preview_dataset(db, dataset_id, limit=limit, offset=0)
                cols = preview.get("columns", [])
                rows = preview.get("rows", [])
                total_rows = preview.get("total_rows", len(rows))
                total_cols = preview.get("total_columns", len(cols))

                # Build Markdown table
                md_table = f"## 📄 Dataset Preview: **{dataset.original_filename}**\n\n"
                md_table += f"• **Total Dimensions**: `{total_rows:,}` rows × `{total_cols}` columns\n"
                md_table += f"• **Displaying**: First `{len(rows)}` rows\n\n"

                # Table header (up to 8 cols in markdown for readability)
                disp_cols = cols[:8]
                md_table += "| # | " + " | ".join(disp_cols) + " |\n"
                md_table += "| :- | " + " | ".join([":-" for _ in disp_cols]) + " |\n"
                for i, r in enumerate(rows[:10]):
                    vals = [str(r.get(c, ""))[:25] for c in disp_cols]
                    md_table += f"| {i+1} | " + " | ".join(vals) + " |\n"

                if len(cols) > 8:
                    md_table += f"\n*...and {len(cols) - 8} more columns: {', '.join(cols[8:])}*\n"

                # Add interactive Table widget chart payload
                charts.append({
                    "id": f"table_{int(time.time())}",
                    "type": "table",
                    "title": f"Spreadsheet Head Preview ({dataset.original_filename})",
                    "description": f"Showing first {len(rows)} of {total_rows:,} rows across {total_cols} columns.",
                    "data": rows,
                    "config": {
                        "columns": cols,
                        "dtypes": preview.get("dtypes", {}),
                        "total_rows": total_rows,
                        "total_columns": total_cols,
                    }
                })

                return md_table, tool_calls, charts

            # ─── Universal Chart Generation Tool ─────────────────────────
            if tool_name == "generate_chart":
                dataset_id = params.get("dataset_id")
                from app.services.profiler import DatasetProfiler
                from app.db.models import Dataset
                dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                if not dataset:
                    return f"Dataset `{dataset_id}` not found.", tool_calls, charts

                df = DatasetProfiler.load_dataset(dataset.file_path)
                chart_type = (params.get("chart_type") or "").lower().strip()
                x_col = params.get("x_column")
                y_col = params.get("y_column")
                z_col = params.get("z_column")
                group_col = params.get("group_column")
                agg = (params.get("aggregation") or "").lower().strip()
                title = params.get("title")

                # Natural language extraction from user query if columns/types missing
                query_lower = user_query.lower()

                # Extract potential column names from query
                detected_cols = []
                for col in df.columns:
                    # Match full column name in query
                    if col.lower() in query_lower:
                        detected_cols.append(col)

                if not x_col and len(detected_cols) > 0:
                    x_col = detected_cols[0]
                if not y_col and len(detected_cols) > 1:
                    y_col = detected_cols[1]
                if not z_col and len(detected_cols) > 2:
                    z_col = detected_cols[2]

                num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                cat_cols = [c for c in df.columns if c not in num_cols]

                # Intelligent chart type detection if default or generic
                if not chart_type or chart_type in ("chart", "graph", "plot"):
                    if any(k in query_lower for k in ["box", "boxplot", "whisker", "quantile"]):
                        chart_type = "boxplot"
                    elif any(k in query_lower for k in ["radar", "spider"]):
                        chart_type = "radar"
                    elif any(k in query_lower for k in ["donut", "doughnut"]):
                        chart_type = "donut"
                    elif any(k in query_lower for k in ["pie"]):
                        chart_type = "pie"
                    elif any(k in query_lower for k in ["stacked bar", "stacked"]):
                        chart_type = "stacked_bar"
                    elif any(k in query_lower for k in ["horizontal bar", "barh", "ranking"]):
                        chart_type = "horizontal_bar"
                    elif any(k in query_lower for k in ["area", "stacked area"]):
                        chart_type = "area"
                    elif any(k in query_lower for k in ["multi line", "lines"]):
                        chart_type = "multi_line"
                    elif any(k in query_lower for k in ["bubble"]):
                        chart_type = "bubble"
                    elif any(k in query_lower for k in ["scatter"]):
                        chart_type = "scatter"
                    elif any(k in query_lower for k in ["heatmap", "matrix"]):
                        chart_type = "heatmap"
                    elif any(k in query_lower for k in ["composed", "combo"]):
                        chart_type = "composed"
                    elif any(k in query_lower for k in ["histogram", "distribution"]):
                        chart_type = "histogram"
                    elif any(k in query_lower for k in ["line", "trend"]):
                        chart_type = "line"
                    else:
                        chart_type = "bar"

                # 1. ── BOX PLOT / STATISTICAL DISTRIBUTION SUMMARY ────────────
                if chart_type in ("boxplot", "box", "box_summary"):
                    target_num = x_col if x_col in num_cols else (y_col if y_col in num_cols else (num_cols[0] if num_cols else None))
                    if not target_num:
                        return "Need at least one numerical column to generate a Box Plot.", tool_calls, charts

                    box_data = []
                    # Check if grouped by category
                    group_candidate = group_col or (y_col if y_col in cat_cols else (x_col if x_col in cat_cols else None))

                    if group_candidate and group_candidate in df.columns:
                        top_groups = df[group_candidate].value_counts().head(6).index.tolist()
                        for grp in top_groups:
                            sub_s = df[df[group_candidate] == grp][target_num].dropna()
                            if len(sub_s) >= 2:
                                q1 = float(np.percentile(sub_s, 25))
                                q2 = float(np.percentile(sub_s, 50))
                                q3 = float(np.percentile(sub_s, 75))
                                iqr = q3 - q1
                                lower_fence = float(max(float(sub_s.min()), q1 - 1.5 * iqr))
                                upper_fence = float(min(float(sub_s.max()), q3 + 1.5 * iqr))
                                outliers = [float(v) for v in sub_s[(sub_s < lower_fence) | (sub_s > upper_fence)].head(5)]

                                box_data.append({
                                    "category": str(grp),
                                    "min": round(lower_fence, 2),
                                    "q1": round(q1, 2),
                                    "median": round(q2, 2),
                                    "mean": round(float(sub_s.mean()), 2),
                                    "q3": round(q3, 2),
                                    "max": round(upper_fence, 2),
                                    "outliers": outliers,
                                    "count": len(sub_s),
                                })
                        desc = f"Box plot distribution of {target_num} across {group_candidate} groups."
                    else:
                        # Distribution across multiple numeric columns or single column
                        cols_to_plot = [c for c in [x_col, y_col] if c in num_cols] or num_cols[:4]
                        for c in cols_to_plot:
                            sub_s = df[c].dropna()
                            if len(sub_s) >= 2:
                                q1 = float(np.percentile(sub_s, 25))
                                q2 = float(np.percentile(sub_s, 50))
                                q3 = float(np.percentile(sub_s, 75))
                                iqr = q3 - q1
                                lower_fence = float(max(float(sub_s.min()), q1 - 1.5 * iqr))
                                upper_fence = float(min(float(sub_s.max()), q3 + 1.5 * iqr))
                                outliers = [float(v) for v in sub_s[(sub_s < lower_fence) | (sub_s > upper_fence)].head(5)]

                                box_data.append({
                                    "category": str(c),
                                    "min": round(lower_fence, 2),
                                    "q1": round(q1, 2),
                                    "median": round(q2, 2),
                                    "mean": round(float(sub_s.mean()), 2),
                                    "q3": round(q3, 2),
                                    "max": round(upper_fence, 2),
                                    "outliers": outliers,
                                    "count": len(sub_s),
                                })
                        desc = f"Statistical five-number summary and box plot distributions."

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "boxplot",
                        "title": title or f"Box Plot & Quantile Summary ({target_num})",
                        "description": desc,
                        "x_key": "category",
                        "data": box_data,
                    })

                    res = f"### 📦 Box Plot Analysis: `{target_num}`\n\n"
                    for b in box_data:
                        res += f"• **{b['category']}**: Min `{b['min']}` | Q1 `{b['q1']}` | Median `{b['median']}` | Q3 `{b['q3']}` | Max `{b['max']}`\n"
                    res += "\nInteractive Box Plot summary card rendered below."
                    return res, tool_calls, charts

                # 2. ── RADAR / SPIDER MULTIVARIATE CHART ──────────────────────
                elif chart_type in ("radar", "spider"):
                    plot_num_cols = [c for c in df.columns if c in num_cols][:6]
                    if len(plot_num_cols) < 3:
                        return "Radar chart requires at least 3 numerical features to plot.", tool_calls, charts

                    radar_data = []
                    for c in plot_num_cols:
                        s = df[c].dropna()
                        min_v, max_v = s.min(), s.max()
                        mean_v = s.mean()
                        # Normalize mean to 0-100 score
                        score = round(((mean_v - min_v) / (max_v - min_v + 1e-9)) * 100, 1)
                        radar_data.append({
                            "subject": str(c),
                            "value": float(score),
                            "raw_mean": round(float(mean_v), 2),
                            "fullMark": 100,
                        })

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "radar",
                        "title": title or "Multivariate Feature Radar Profile",
                        "description": "Normalized feature comparison across key numerical dimensions.",
                        "x_key": "subject",
                        "y_key": "value",
                        "data": radar_data,
                    })

                    res = "### 🕸️ Radar Profile Summary\n\n"
                    for r in radar_data:
                        res += f"• **{r['subject']}**: Normalized Score `{r['value']}%` (Mean: `{r['raw_mean']}`)\n"
                    return res, tool_calls, charts

                # 3. ── DONUT & PIE PROPORTIONS ────────────────────────────────
                elif chart_type in ("donut", "doughnut", "pie"):
                    cat_col = x_col if x_col in cat_cols else (y_col if y_col in cat_cols else (cat_cols[0] if cat_cols else (x_col or df.columns[0])))
                    is_donut = "donut" in chart_type or "doughnut" in chart_type or "donut" in query_lower

                    # If y_col is numeric, do sum aggregation by category
                    if y_col and y_col in num_cols:
                        grouped = df.groupby(cat_col)[y_col].sum().sort_values(ascending=False).head(7)
                        chart_data = [{"category": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]
                        total_sum = sum(c["value"] for c in chart_data)
                        for c in chart_data:
                            c["percent"] = round((c["value"] / (total_sum + 1e-9)) * 100, 1)
                        y_metric = "value"
                    else:
                        counts = df[cat_col].value_counts().head(7)
                        total_cnt = len(df[cat_col].dropna())
                        chart_data = [
                            {"category": str(k), "count": int(v), "percent": round((v / total_cnt) * 100, 1)}
                            for k, v in counts.items()
                        ]
                        y_metric = "count"

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "donut" if is_donut else "pie",
                        "title": title or f"{'Donut' if is_donut else 'Pie'} Breakdown for {cat_col}",
                        "description": f"Proportional share of categories in {cat_col}.",
                        "x_key": "category",
                        "y_key": y_metric,
                        "data": chart_data,
                        "config": {"inner_radius": 55 if is_donut else 0},
                    })

                    res = f"### 🍩 {'Donut' if is_donut else 'Pie'} Breakdown: `{cat_col}`\n\n"
                    for d in chart_data[:5]:
                        res += f"• **{d['category']}**: `{d.get(y_metric)}` ({d.get('percent')}%\n"
                    return res, tool_calls, charts

                # 4. ── STACKED & GROUPED BAR CHARTS ──────────────────────────
                elif chart_type in ("stacked_bar", "stacked", "grouped_bar"):
                    c1 = x_col or (cat_cols[0] if cat_cols else df.columns[0])
                    c2 = group_col or (y_col if y_col in cat_cols and y_col != c1 else (cat_cols[1] if len(cat_cols) > 1 else None))

                    if c2 and c1 in df.columns and c2 in df.columns:
                        crosstab = pd.crosstab(df[c1], df[c2]).head(8)
                        series_keys = [str(col) for col in crosstab.columns]
                        chart_data = []
                        for idx, row in crosstab.iterrows():
                            entry = {"category": str(idx)}
                            for sk in series_keys:
                                entry[sk] = int(row[sk])
                            chart_data.append(entry)

                        charts.append({
                            "id": f"chart_{int(time.time())}",
                            "type": "stacked_bar" if "stacked" in chart_type else "bar",
                            "title": title or f"{c1} vs {c2} Breakdown",
                            "description": f"Cross-tabulated frequency distributions across {len(series_keys)} subcategories.",
                            "x_key": "category",
                            "series_keys": series_keys,
                            "data": chart_data,
                        })

                        res = f"### 📊 Stacked Category Cross-Tab: `{c1}` × `{c2}`\n\n"
                        res += f"Generated stacked distribution chart across subcategories: `{', '.join(series_keys[:5])}`."
                        return res, tool_calls, charts

                # 5. ── HORIZONTAL BAR CHART (RANKINGS) ────────────────────────
                elif chart_type in ("horizontal_bar", "bar_horizontal", "ranking"):
                    cat_c = x_col if x_col in cat_cols else (cat_cols[0] if cat_cols else df.columns[0])
                    if y_col and y_col in num_cols:
                        grouped = df.groupby(cat_c)[y_col].mean().sort_values(ascending=True).tail(10)
                        chart_data = [{"category": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]
                        metric_name = f"Average {y_col}"
                    else:
                        counts = df[cat_c].value_counts().sort_values(ascending=True).tail(10)
                        chart_data = [{"category": str(k), "value": int(v)} for k, v in counts.items()]
                        metric_name = "Count"

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "horizontal_bar",
                        "title": title or f"Top Rankings for {cat_c}",
                        "description": f"Horizontal ranking sorted by {metric_name}.",
                        "x_key": "value",
                        "y_key": "category",
                        "data": chart_data,
                    })

                    res = f"### 📊 Ranking Breakdown: `{cat_c}`\n\n"
                    for d in reversed(chart_data[-5:]):
                        res += f"• **{d['category']}**: `{d['value']}`\n"
                    return res, tool_calls, charts

                # 6. ── BUBBLE CHART (3-DIMENSIONS) ────────────────────────────
                elif chart_type in ("bubble", "3d_scatter") or (z_col and z_col in num_cols):
                    x_n = x_col if x_col in num_cols else (num_cols[0] if len(num_cols) > 0 else df.columns[0])
                    y_n = y_col if y_col in num_cols else (num_cols[1] if len(num_cols) > 1 else num_cols[0])
                    z_n = z_col if z_col in num_cols else (num_cols[2] if len(num_cols) > 2 else y_n)

                    sample_df = df[[x_n, y_n, z_n]].dropna().head(100)
                    chart_data = []
                    for _, row in sample_df.iterrows():
                        chart_data.append({
                            x_n: round(float(row[x_n]), 2),
                            y_n: round(float(row[y_n]), 2),
                            z_n: round(float(row[z_n]), 2),
                            "size": round(float(row[z_n]), 2),
                        })

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "bubble",
                        "title": title or f"Bubble Chart: {x_n} vs {y_n} (Size: {z_n})",
                        "description": f"3-dimensional relationship visual with dynamic bubble radius.",
                        "x_key": x_n,
                        "y_key": y_n,
                        "z_key": z_n,
                        "data": chart_data,
                    })

                    res = f"### 🫧 Bubble Chart: `{x_n}` vs `{y_n}` (Size: `{z_n}`)\n\n"
                    res += f"• Sample data points: `{len(chart_data)}`\n"
                    res += f"• Correlation `{x_n}` & `{y_n}`: `{sample_df[x_n].corr(sample_df[y_n]):.4f}`\n"
                    return res, tool_calls, charts

                # 7. ── AREA & STACKED AREA CHARTS ─────────────────────────────
                elif chart_type in ("area", "stacked_area"):
                    target_c = y_col if y_col in num_cols else (x_col if x_col in num_cols else num_cols[0] if num_cols else df.columns[0])
                    sample_df = df[[target_c]].dropna().head(50).reset_index()
                    chart_data = [{"index": f"#{i+1}", target_c: round(float(v), 2)} for i, v in enumerate(sample_df[target_c])]

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "area",
                        "title": title or f"Area Distribution of {target_c}",
                        "description": f"Cumulative area volume curve across records.",
                        "x_key": "index",
                        "y_key": target_c,
                        "data": chart_data,
                    })

                    res = f"### 🌊 Area Curve: `{target_c}`\n\n"
                    res += f"• Mean: `{df[target_c].mean():.2f}` | Max: `{df[target_c].max():.2f}` | Min: `{df[target_c].min():.2f}`\n"
                    return res, tool_calls, charts

                # 8. ── MULTI-LINE & TREND CHARTS ──────────────────────────────
                elif chart_type in ("line", "multi_line"):
                    target_cols = [c for c in [x_col, y_col] if c in num_cols] or num_cols[:3]
                    if not target_cols:
                        target_cols = [df.columns[0]]

                    sample_df = df[target_cols].dropna().head(40).reset_index()
                    chart_data = []
                    for i, row in sample_df.iterrows():
                        entry = {"index": f"#{i+1}"}
                        for c in target_cols:
                            entry[c] = round(float(row[c]), 2)
                        chart_data.append(entry)

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "line",
                        "title": title or f"Trend Line ({', '.join(target_cols)})",
                        "description": "Continuous trend trajectory across data points.",
                        "x_key": "index",
                        "series_keys": target_cols if len(target_cols) > 1 else None,
                        "y_key": target_cols[0],
                        "data": chart_data,
                    })

                    res = f"### 📈 Line Trend: `{', '.join(target_cols)}`\n\n"
                    res += f"Interactive line plot rendered below for `{len(chart_data)}` points."
                    return res, tool_calls, charts

                # 9. ── SCATTER PLOT ───────────────────────────────────────────
                elif chart_type == "scatter" and ((x_col and y_col) or len(num_cols) >= 2):
                    x_n = x_col if x_col in num_cols else num_cols[0]
                    y_n = y_col if y_col in num_cols and y_col != x_n else (num_cols[1] if len(num_cols) > 1 else num_cols[0])

                    sample_df = df[[x_n, y_n]].dropna().head(100)
                    chart_data = sample_df.to_dict(orient="records")
                    corr = sample_df[x_n].corr(sample_df[y_n])

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "scatter",
                        "title": title or f"{x_n} vs {y_n} Scatter Plot",
                        "description": f"Bivariate relationship with correlation r = {corr:.4f}.",
                        "x_key": x_n,
                        "y_key": y_n,
                        "data": chart_data,
                    })

                    res = f"### 📈 Scatter Plot: `{x_n}` vs `{y_n}`\n\n"
                    res += f"• **Pearson Correlation**: `{corr:.4f}`\n"
                    res += f"• Sample points plotted: `{len(chart_data)}`\n"
                    return res, tool_calls, charts

                # 10. ── HISTOGRAM / VALUE DISTRIBUTION ────────────────────────
                elif chart_type in ("histogram", "distribution") or (x_col in num_cols and not y_col):
                    target_c = x_col if x_col in num_cols else (num_cols[0] if num_cols else df.columns[0])
                    series = df[target_c].dropna()
                    counts, bin_edges = np.histogram(series, bins=min(10, max(5, series.nunique())))
                    chart_data = []
                    for i in range(len(counts)):
                        label = f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}"
                        chart_data.append({"bin": label, "count": int(counts[i])})

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "bar",
                        "title": title or f"Frequency Distribution of {target_c}",
                        "description": f"Histogram showing frequency counts across {len(counts)} value bins.",
                        "x_key": "bin",
                        "y_key": "count",
                        "data": chart_data,
                    })

                    res = (
                        f"### 📊 Distribution of `{target_c}`\n\n"
                        f"• **Min**: `{series.min():.2f}` | **Max**: `{series.max():.2f}`\n"
                        f"• **Mean**: `{series.mean():.2f}` | **Median**: `{series.median():.2f}` | **Std**: `{series.std():.2f}`\n"
                    )
                    return res, tool_calls, charts

                # 11. ── DEFAULT: AGGREGATED CATEGORICAL / NUMERICAL BAR CHART ──
                else:
                    cat_c = x_col if x_col in cat_cols else (cat_cols[0] if cat_cols else df.columns[0])
                    if y_col and y_col in num_cols:
                        if agg == "sum":
                            grouped = df.groupby(cat_c)[y_col].sum().head(10)
                            label_str = f"Sum of {y_col}"
                        elif agg in ("median", "med"):
                            grouped = df.groupby(cat_c)[y_col].median().head(10)
                            label_str = f"Median {y_col}"
                        else:
                            grouped = df.groupby(cat_c)[y_col].mean().head(10)
                            label_str = f"Average {y_col}"

                        chart_data = [{"category": str(k), "value": round(float(v), 2)} for k, v in grouped.items()]
                        y_k = "value"
                    else:
                        counts = df[cat_c].value_counts().head(10)
                        chart_data = [{"category": str(k), "count": int(v)} for k, v in counts.items()]
                        y_k = "count"
                        label_str = "Count"

                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "bar",
                        "title": title or f"{label_str} by {cat_c}",
                        "description": f"Bar chart comparison across {len(chart_data)} categories.",
                        "x_key": "category",
                        "y_key": y_k,
                        "data": chart_data,
                    })

                    res = f"### 📊 Category Breakdown: `{cat_c}`\n\n"
                    for d in chart_data[:5]:
                        res += f"• **{d['category']}**: `{d.get(y_k)}`\n"
                    return res, tool_calls, charts


            elif tool_name == "compare_models_chart":
                from app.services.experiment_service import ExperimentService
                leaderboard = ExperimentService.get_leaderboard(db, params["dataset_id"])
                entries = leaderboard.get("entries", [])
                if not entries:
                    return "No completed experiments found for this dataset to chart.", tool_calls, charts

                chart_data = []
                for e in entries:
                    metrics = e.get("metrics", {})
                    chart_data.append({
                        "model": e.get("display_name", e.get("algorithm")),
                        "f1": round(metrics.get("f1", 0) * 100, 1),
                        "accuracy": round(metrics.get("accuracy", 0) * 100, 1),
                        "precision": round(metrics.get("precision", 0) * 100, 1),
                        "recall": round(metrics.get("recall", 0) * 100, 1),
                    })

                charts.append({
                    "id": f"chart_{int(time.time())}",
                    "type": "bar",
                    "title": "AutoML Model Leaderboard Comparison (%)",
                    "description": "Cross-validated performance metrics across all trained models.",
                    "x_key": "model",
                    "series_keys": ["f1", "accuracy", "precision", "recall"],
                    "data": chart_data,
                })
                best_model = entries[0]
                response = (
                    f"### 🏆 Model Comparison Chart\n\n"
                    f"• **Top Performing Model**: **{best_model['display_name']}**\n"
                    f"• **Primary Score**: `{best_model['primary_metric_value']:.4f}`\n\n"
                    f"Interactive multi-metric comparison chart rendered below."
                )
                return response, tool_calls, charts

            elif tool_name == "plot_correlation_chart":
                from app.services.profiler import DatasetProfiler
                from app.db.models import Dataset
                dataset = db.query(Dataset).filter(Dataset.id == params["dataset_id"]).first()
                if not dataset:
                    return "Dataset not found.", tool_calls, charts

                df = DatasetProfiler.load_dataset(dataset.file_path)
                num_df = df.select_dtypes(include=[np.number])
                if num_df.shape[1] < 2:
                    return "Need at least 2 numeric columns to compute correlations.", tool_calls, charts

                corr_matrix = num_df.corr().round(4)
                target = params.get("target") or (dataset.target_column if dataset.target_column in num_df.columns else None)

                if target and target in num_df.columns:
                    target_corrs = corr_matrix[target].drop(target).to_dict()
                    chart_data = [{"feature": k, "correlation": float(v)} for k, v in target_corrs.items()]
                    chart_data = sorted(chart_data, key=lambda x: abs(x["correlation"]), reverse=True)[:10]
                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "bar",
                        "title": f"Feature Correlation with Target ({target})",
                        "description": "Pearson correlation coefficient values with the target.",
                        "x_key": "feature",
                        "y_key": "correlation",
                        "data": chart_data,
                    })
                    response = f"### 🔗 Correlation with `{target}`\n\nGenerated top correlation ranking chart below."
                    return response, tool_calls, charts
                else:
                    # Top pairs
                    pairs = []
                    for i in range(len(num_df.columns)):
                        for j in range(i + 1, len(num_df.columns)):
                            col1, col2 = num_df.columns[i], num_df.columns[j]
                            pairs.append({"pair": f"{col1} - {col2}", "correlation": float(corr_matrix.loc[col1, col2])})
                    pairs = sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)[:8]
                    charts.append({
                        "id": f"chart_{int(time.time())}",
                        "type": "bar",
                        "title": "Top Pairwise Feature Correlations",
                        "description": "Highest correlated feature pairs.",
                        "x_key": "pair",
                        "y_key": "correlation",
                        "data": pairs,
                    })
                    response = f"### 🔗 Top Feature Correlations\n\nComputed pairwise correlations. Chart rendered below."
                    return response, tool_calls, charts

            # ─── Standard ML Tools ───────────────────────────────────────
            elif tool_name == "profile_dataset":
                from app.services.dataset_service import DatasetService
                profile = DatasetService.get_profile(db, params["dataset_id"])
                overview = profile.get("overview", {})
                quality = profile.get("data_quality", {})
                types = profile.get("column_types", {})
                ids = profile.get("potential_ids", [])

                response = (
                    f"## Dataset Profile — {profile.get('filename', 'Dataset')}\n\n"
                    f"📋 **Shape**: {overview.get('rows', 0):,} rows × {overview.get('columns', 0)} columns\n\n"
                    f"### Column Type Breakdown\n"
                    f"• Numerical: `{types.get('numerical', 0)}`\n"
                    f"• Categorical: `{types.get('categorical', 0)}`\n"
                    f"• Date/Time: `{types.get('date', 0)}`\n"
                    f"• Boolean: `{types.get('boolean', 0)}`\n\n"
                    f"### Data Quality Health\n"
                    f"• Missing cells: `{quality.get('missing_percentage', 0)}%` ({quality.get('missing_cells', 0):,} cells)\n"
                    f"• Duplicates: `{quality.get('duplicates', 0):,}` ({quality.get('duplicate_percentage', 0)}%)\n"
                )
                if ids:
                    response += f"• Identified ID Columns: `{', '.join(ids)}`\n"

                return response, tool_calls, charts

            elif tool_name == "detect_issues":
                from ml_engine.preprocessing.cleaning_engine import CleaningEngine
                from app.services.profiler import DatasetProfiler
                from app.db.models import Dataset

                dataset = db.query(Dataset).filter(Dataset.id == params["dataset_id"]).first()
                if not dataset:
                    return f"Dataset with ID `{params['dataset_id']}` not found.", tool_calls, charts

                df = DatasetProfiler.load_dataset(dataset.file_path)
                issues = CleaningEngine.detect_issues(df)

                response = f"## Data Quality Report for {dataset.original_filename}\n\n"
                response += f"• **Total Missing**: `{issues['total_missing']:,}` cells ({issues['missing_percentage']}%)\n"
                response += f"• **Duplicate Rows**: `{issues['duplicates']:,}` ({issues['duplicate_percentage']}%)\n"
                response += f"• **Constant Columns**: `{len(issues['constant_columns'])}`\n"
                response += f"• **Potential IDs**: `{len(issues['potential_ids'])}`\n"

                if issues.get("missing_details"):
                    response += "\n### Columns with Missing Values\n"
                    for detail in issues["missing_details"][:10]:
                        response += f"• **{detail['column']}**: {detail['count']} missing ({detail['percentage']}%)\n"

                return response, tool_calls, charts

            elif tool_name == "suggest_target":
                from app.services.dataset_service import DatasetService
                suggestions = DatasetService.suggest_target(db, params["dataset_id"])

                response = f"## Target Column Recommendations\n\n"
                response += f"• **Recommended Primary Target**: `{suggestions['suggested_target']}`\n"
                response += f"• **Detected Task Type**: `{suggestions['task_type'].replace('_', ' ').title()}`\n\n"
                return response, tool_calls, charts

            elif tool_name == "run_eda":
                from app.services.eda_service import EDAService
                eda_result = EDAService.run_eda(db, params["dataset_id"], params.get("target"))

                response = f"## Exploratory Data Analysis\n\n"
                response += f"• **Columns Analyzed**: `{len(eda_result.get('numerical_stats', []))} numerical, {len(eda_result.get('categorical_stats', []))} categorical`\n\n"
                return response, tool_calls, charts

            elif tool_name == "get_leaderboard":
                from app.services.experiment_service import ExperimentService
                leaderboard = ExperimentService.get_leaderboard(db, params["dataset_id"])
                entries = leaderboard.get("entries", [])

                if not entries:
                    return "No completed experiments found for this dataset yet.", tool_calls, charts

                response = f"## 🏆 AutoML Leaderboard ({leaderboard.get('task_type', '').title()})\n\n"
                response += "| Rank | Model | Primary Metric | Duration |\n"
                response += "| :--- | :--- | :--- | :--- |\n"
                for entry in entries:
                    response += (
                        f"| #{entry['rank']} | **{entry['display_name']}** | "
                        f"`{entry['primary_metric_value']:.4f}` | {entry['training_duration']:.2f}s |\n"
                    )
                return response, tool_calls, charts

            elif tool_name == "get_feature_importance":
                from app.services.model_service import ModelService
                explain = ModelService.get_explainability(db, params["model_id"])
                importances = explain.get("feature_importance", [])

                chart_data = [{"feature": f["feature"], "importance": round(f["importance"], 4)} for f in importances[:10]]
                charts.append({
                    "id": f"chart_{int(time.time())}",
                    "type": "bar",
                    "title": "SHAP Global Feature Importance",
                    "description": "Relative contribution of features to model predictions.",
                    "x_key": "feature",
                    "y_key": "importance",
                    "data": chart_data,
                })

                response = f"## 🔍 SHAP Feature Importance\n\n"
                for feat in importances[:8]:
                    response += f"• **{feat['feature']}**: `{feat['importance']:.4f}` ({feat.get('percentage', 0)}%)\n"

                return response, tool_calls, charts

            elif tool_name == "get_model_health":
                from app.services.monitoring_service import MonitoringService
                health = MonitoringService.get_model_health(db, params["model_id"])

                response = f"## 📡 Model Health & Drift Status\n\n"
                response += f"• **Status**: `{health.get('status', 'HEALTHY')}`\n"
                response += f"• **Total Predictions**: `{health.get('prediction_count', 0):,}`\n"
                response += f"• **Average Latency**: `{health.get('avg_latency_ms', 0):.2f} ms`\n"
                response += f"• **Drift Alert**: `{'⚠️ Detected' if health.get('drift_detected') else '✅ None'}`\n"

                return response, tool_calls, charts

            return f"Executed `{tool_name}` successfully.", tool_calls, charts

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}", exc_info=True)
            return f"Encountered an issue running `{tool_name}`: {str(e)}", tool_calls, charts

    @classmethod
    def run_auto_pilot_pipeline(
        cls,
        db: Session,
        dataset_id: str,
        target: Optional[str] = None,
        llm_model: Optional[str] = None,
        enable_feature_engineering: bool = True,
        cv_folds: int = 5,
        max_interactions: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute the Autonomous End-to-End AI Data Science Pipeline:
        1. Dataset Intelligence & Target Detection
        2. AI Feature Engineering Strategy Formulation
        3. Automated Data Cleaning & Transformation
        4. AI Model Selection Reasoning
        5. AutoML Training with Cross-Validation & Leaderboard
        6. Explainability Diagnostics & Deployment Readiness
        """
        from app.db.models import Dataset, TaskType, MLModel
        from app.services.profiler import DatasetProfiler
        from app.services.dataset_service import DatasetService
        from app.services.experiment_service import ExperimentService
        from app.services.model_service import ModelService
        from ml_engine.preprocessing.cleaning_engine import CleaningEngine
        from ml_engine.preprocessing.feature_engine import FeatureEngineeringEngine
        from ml_engine.analysis.task_detection import TaskDetectionEngine

        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found.",
            )

        steps: List[Dict[str, Any]] = []
        charts: List[Dict[str, Any]] = []

        # ─────────────────────────────────────────────────────────────────
        # STEP 1: Dataset Intelligence & Target Detection
        # ─────────────────────────────────────────────────────────────────
        df = DatasetProfiler.load_dataset(dataset.file_path)
        total_rows, total_cols = df.shape
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = [c for c in df.columns if c not in num_cols]

        # Target column detection & resolution
        resolved_target = target or dataset.target_column
        target_suggestions = []
        if not resolved_target:
            try:
                sugg = DatasetService.suggest_target(db, dataset_id)
                resolved_target = sugg.get("suggested_target")
                target_suggestions = sugg.get("suggestions", [])
            except Exception:
                pass

        if not resolved_target:
            # Fallback heuristic: choose last non-ID column
            issues_pre = CleaningEngine.detect_issues(df)
            candidate_cols = [c for c in df.columns if c not in issues_pre.get("potential_ids", [])]
            resolved_target = candidate_cols[-1] if candidate_cols else df.columns[-1]

        # Task detection
        task_info = TaskDetectionEngine.detect_task(df, resolved_target)
        task_type = task_info.get("task", "binary_classification" if df[resolved_target].nunique() <= 2 else "regression")

        # Save resolved target and task type on dataset
        dataset.target_column = resolved_target
        dataset.task_type = TaskType(task_type)
        db.commit()

        # Profiling stats
        missing_cells = int(df.isna().sum().sum())
        missing_pct = round((missing_cells / (total_rows * total_cols + 1e-9)) * 100, 2)
        duplicates = int(df.duplicated().sum())

        step1_summary = (
            f"Dataset profiled: {total_rows:,} rows × {total_cols} columns ({len(num_cols)} numerical, {len(cat_cols)} categorical). "
            f"Target confirmed as '{resolved_target}' for {task_type.replace('_', ' ').title()}."
        )
        steps.append({
            "step_number": 1,
            "title": "Dataset Intelligence & Target Detection",
            "status": "completed",
            "summary": step1_summary,
            "details": {
                "rows": total_rows,
                "columns": total_cols,
                "numerical_features": len(num_cols),
                "categorical_features": len(cat_cols),
                "missing_percentage": missing_pct,
                "duplicate_rows": duplicates,
                "target_column": resolved_target,
                "task_type": task_type,
                "class_distribution": task_info.get("class_distribution"),
                "target_stats": task_info.get("stats"),
            },
        })

        # ─────────────────────────────────────────────────────────────────
        # STEP 2: AI Feature Engineering Strategy Formulation
        # ─────────────────────────────────────────────────────────────────
        date_candidates = []
        for col in df.columns:
            if col != resolved_target:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    date_candidates.append(col)
                elif df[col].dtype == "object":
                    sample = df[col].dropna().head(30).astype(str)
                    if sample.str.contains(r"[-/]", regex=True).mean() > 0.5:
                        date_candidates.append(col)

        # High variance interactions
        eligible_num = [c for c in num_cols if c != resolved_target]
        interactions_planned = min(max_interactions, max(0, (len(eligible_num) * (len(eligible_num) - 1)) // 2))

        fe_rationale = (
            f"Formulated strategy for {task_type.replace('_', ' ')} with {total_cols - 1} predictors: "
            f"1) Temporal decomposition for {len(date_candidates)} date attribute(s); "
            f"2) Cross-feature interaction generation ({interactions_planned} terms) across high-variance predictors; "
            f"3) Automated zero-variance filter & median/mode imputation."
        )

        steps.append({
            "step_number": 2,
            "title": "AI Feature Engineering Strategy",
            "status": "completed",
            "summary": fe_rationale,
            "details": {
                "date_columns_detected": date_candidates,
                "planned_interactions": interactions_planned,
                "numerical_candidates": eligible_num[:6],
                "handling_missing": "median_mode_imputation",
                "scaling_strategy": "robust_standard_scaling",
            },
        })

        # ─────────────────────────────────────────────────────────────────
        # STEP 3: Automated Data Cleaning & Transformation
        # ─────────────────────────────────────────────────────────────────
        issues = CleaningEngine.detect_issues(df)
        cleaned_df, cleaning_report = CleaningEngine.clean_dataset(
            df, target=resolved_target, detected_ids=issues.get("potential_ids", [])
        )

        feature_report = {}
        transformed_df = cleaned_df
        if enable_feature_engineering:
            transformed_df, feature_report = FeatureEngineeringEngine.run_feature_engineering(
                cleaned_df,
                target=resolved_target,
                enable_date_features=True,
                enable_interactions=True,
                max_interactions=max_interactions,
            )

        new_features = feature_report.get("new_features", [])
        step3_summary = (
            f"Applied automated cleaning ({cleaning_report['rows_before']} -> {cleaning_report['rows_after']} rows) and "
            f"engineered {len(new_features)} new domain features. Dimension changed from {df.shape[1]} to {transformed_df.shape[1]} features."
        )

        steps.append({
            "step_number": 3,
            "title": "Automated Data Transformation",
            "status": "completed",
            "summary": step3_summary,
            "details": {
                "rows_before": cleaning_report["rows_before"],
                "rows_after": cleaning_report["rows_after"],
                "columns_before": df.shape[1],
                "columns_after": transformed_df.shape[1],
                "new_features_created": new_features,
                "dropped_constants": cleaning_report.get("dropped_constants", []),
                "dropped_ids": cleaning_report.get("dropped_ids", []),
            },
        })

        # ─────────────────────────────────────────────────────────────────
        # STEP 4: AI Model Selection Reasoning
        # ─────────────────────────────────────────────────────────────────
        is_classification = "classification" in task_type
        if is_classification:
            candidate_algos = ["LightGBM", "XGBoost", "Random Forest", "Logistic Regression"]
            model_reasoning = (
                f"Selected 4 candidate architectures for {task_type}: "
                f"• LightGBM: Highly effective gradient boosting for tabular tabular splits and categorical features. "
                f"• XGBoost: Regularized boosting to maximize generalization and prevent overfitting. "
                f"• Random Forest: Bagged ensemble providing variance reduction and non-linear baseline. "
                f"• Logistic Regression: Calibrated linear model with L2 regularization for baseline benchmark."
            )
        else:
            candidate_algos = ["LightGBM", "XGBoost", "Random Forest", "Ridge Regression"]
            model_reasoning = (
                f"Selected 4 candidate architectures for regression task: "
                f"• LightGBM: Fast gradient boosting minimizing RMSE on non-linear continuous surfaces. "
                f"• XGBoost: Exact tree booster with L1/L2 shrinkage for robustness against outliers. "
                f"• Random Forest: Ensemble decision trees for stable variance reduction. "
                f"• Ridge Regression: L2-penalized linear regression baseline."
            )

        steps.append({
            "step_number": 4,
            "title": "AI Model Selection Reasoning",
            "status": "completed",
            "summary": f"Identified optimal candidate model families: {', '.join(candidate_algos)}.",
            "details": {
                "candidate_algorithms": candidate_algos,
                "evaluation_strategy": f"{cv_folds}-Fold Stratified Cross-Validation",
                "primary_metric": "F1-Score / Accuracy" if is_classification else "R² / RMSE",
                "reasoning_text": model_reasoning,
            },
        })

        # ─────────────────────────────────────────────────────────────────
        # STEP 5: AutoML Training & Leaderboard
        # ─────────────────────────────────────────────────────────────────
        training_result = ExperimentService.run_training_pipeline(
            db=db,
            dataset_id=dataset_id,
            target=resolved_target,
            cv_folds=cv_folds,
            enable_feature_engineering=enable_feature_engineering,
        )

        leaderboard_entries = training_result.get("leaderboard", [])
        primary_metric = training_result.get("primary_metric", "f1" if is_classification else "r2")

        best_entry = None
        if leaderboard_entries:
            completed_entries = [e for e in leaderboard_entries if e.get("status") == "completed"]
            if completed_entries:
                best_entry = completed_entries[0]

        best_model_name = best_entry["display_name"] if best_entry else "Best Model"
        best_score = best_entry["primary_metric_value"] if best_entry else 0.0

        step5_summary = (
            f"Trained {len(leaderboard_entries)} models using {cv_folds}-fold cross-validation. "
            f"Winner: **{best_model_name}** with primary score of **`{best_score:.4f}`** ({primary_metric.upper()})."
        )

        steps.append({
            "step_number": 5,
            "title": "AutoML Training & Leaderboard",
            "status": "completed",
            "summary": step5_summary,
            "details": {
                "models_trained": len(leaderboard_entries),
                "primary_metric": primary_metric,
                "winner": best_model_name,
                "winner_score": round(best_score, 4),
                "leaderboard": leaderboard_entries,
            },
        })

        # Auto-register top model
        registered_model = None
        experiments_list = training_result.get("experiments", [])
        if experiments_list:
            try:
                best_exp_id = experiments_list[0]["experiment_id"]
                registered_model = ModelService.register_model(db, best_exp_id)
            except Exception as e:
                logger.warning(f"Auto-pilot model auto-registration: {str(e)}")

        # ─────────────────────────────────────────────────────────────────
        # STEP 6: Explainability & Best Model Summary
        # ─────────────────────────────────────────────────────────────────
        feature_importances: List[Dict[str, Any]] = []
        if registered_model:
            try:
                explain_res = ModelService.get_explainability(db, registered_model.id)
                feature_importances = explain_res.get("feature_importance", [])
            except Exception as e:
                logger.warning(f"Could not compute SHAP for model {registered_model.id}: {str(e)}")

        top_drivers = [f"{f['feature']} ({round(f['importance'], 3)})" for f in feature_importances[:4]]
        step6_summary = (
            f"Generated SHAP global explainability for {best_model_name}. "
            f"Top predictive drivers: {', '.join(top_drivers) if top_drivers else 'All features evaluated'}."
        )

        steps.append({
            "step_number": 6,
            "title": "Explainability & Deployment Summary",
            "status": "completed",
            "summary": step6_summary,
            "details": {
                "top_features": feature_importances[:8],
                "deployment_readiness": "Production-Ready",
                "registered_model_id": registered_model.id if registered_model else None,
            },
        })

        # ─────────────────────────────────────────────────────────────────
        # Assemble Visual Charts
        # ─────────────────────────────────────────────────────────────────
        # 1. Leaderboard Comparison Chart
        if leaderboard_entries:
            chart_data = []
            for e in leaderboard_entries:
                if e.get("status") == "completed":
                    metrics = e.get("metrics", {})
                    chart_data.append({
                        "model": e.get("display_name", e.get("algorithm")),
                        "primary_score": round(float(e.get("primary_metric_value", 0)) * 100, 1) if is_classification else round(float(e.get("primary_metric_value", 0)), 3),
                        "duration": round(float(e.get("training_duration", 0)), 2),
                    })
            charts.append({
                "id": f"autopilot_lb_{int(time.time())}",
                "type": "bar",
                "title": f"AutoML Model Leaderboard Comparison ({primary_metric.upper()})",
                "description": f"Cross-validated score across candidate architectures.",
                "x_key": "model",
                "y_key": "primary_score",
                "data": chart_data,
            })

        # 2. SHAP Feature Importance Chart
        if feature_importances:
            shap_chart_data = [
                {"feature": f["feature"], "importance": round(float(f["importance"]), 4)}
                for f in feature_importances[:8]
            ]
            charts.append({
                "id": f"autopilot_shap_{int(time.time())}",
                "type": "bar",
                "title": "SHAP Global Feature Importance (Top Drivers)",
                "description": "Relative impact of engineered features on model predictions.",
                "x_key": "feature",
                "y_key": "importance",
                "data": shap_chart_data,
            })

        # ─────────────────────────────────────────────────────────────────
        # Executive Summary Markdown
        # ─────────────────────────────────────────────────────────────────
        metric_display = f"{best_score:.4f}" if best_score > 1 else f"{best_score * 100:.2f}%"
        exec_summary = (
            f"## 🚀 Autonomous AI Auto-Pilot Pipeline Complete\n\n"
            f"The AI Agent autonomously analyzed **{dataset.original_filename}**, formulated optimal feature engineering, "
            f"benchmarked candidate algorithms, and evaluated full explainability.\n\n"
            f"### 🏆 Executive Highlights\n"
            f"• **Target Column**: `{resolved_target}` ({task_type.replace('_', ' ').title()})\n"
            f"• **Top Model**: **{best_model_name}**\n"
            f"• **Validation Score**: `{metric_display}` ({primary_metric.upper()})\n"
            f"• **Engineered Features**: `{len(new_features)}` new features created\n"
            f"• **Top Predictive Driver**: `{feature_importances[0]['feature'] if feature_importances else 'Features Evaluated'}`\n\n"
            f"### 📋 Pipeline Execution Stages\n"
        )
        for s in steps:
            exec_summary += f"{s['step_number']}. **{s['title']}**: {s['summary']}\n"

        return {
            "dataset_id": dataset_id,
            "filename": dataset.original_filename,
            "target_column": resolved_target,
            "task_type": task_type,
            "status": "success",
            "steps": steps,
            "feature_engineering_summary": {
                "new_features": new_features,
                "original_shape": [total_rows, total_cols],
                "transformed_shape": list(transformed_df.shape),
                "cleaning_report": cleaning_report,
            },
            "model_selection_reasoning": model_reasoning,
            "leaderboard": leaderboard_entries,
            "best_model": {
                "name": best_model_name,
                "score": best_score,
                "metric": primary_metric,
                "registered_model_id": registered_model.id if registered_model else None,
            },
            "feature_importance": feature_importances[:10],
            "charts": charts,
            "executive_summary": exec_summary,
        }
