from fastapi import APIRouter
from app.api.routes import auth, datasets, health, jobs, eda, cleaning, task, experiments, models, agent, feature_engineering, multi_agent, dashboard, forecasting, projects, data_quality, unsupervised

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(datasets.router)
api_router.include_router(data_quality.router)
api_router.include_router(jobs.router)
api_router.include_router(eda.router)
api_router.include_router(cleaning.router)
api_router.include_router(task.router)
api_router.include_router(feature_engineering.router)
api_router.include_router(experiments.router)
api_router.include_router(models.router)
api_router.include_router(agent.router)
api_router.include_router(multi_agent.router)
api_router.include_router(dashboard.router)
api_router.include_router(forecasting.router)
api_router.include_router(unsupervised.router)


