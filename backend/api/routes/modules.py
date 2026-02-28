"""
api/routes/modules.py
---------------------
Endpoints for discovering available training modules and scenarios.
Used when the frontend connects to load the module selector.

GET /modules         — list all modules with their scenarios
GET /modules/{id}    — list scenarios for a module (id, title)

Owner: API team
Depends on: utilities/module_loader
"""

from fastapi import APIRouter, Depends

from api.deps import get_module_loader
from utilities.module_loader import ModuleLoader

router = APIRouter()


@router.get("")
async def list_modules(
    module_loader: ModuleLoader = Depends(get_module_loader),
):
    """
    Return all modules with their scenarios.
    Used to populate the module/scenario selector when the app connects.

    Returns: [
      { module_id: str, scenarios: [ { id: str, title: str } ] }
    ]
    """
    module_ids = module_loader.list_modules()
    result = []
    for mod_id in module_ids:
        scenario_ids = module_loader.list_scenarios(mod_id)
        scenarios = [
            module_loader.get_scenario_info(mod_id, sid)
            for sid in scenario_ids
        ]
        result.append({
            "module_id": mod_id,
            "scenarios": scenarios,
        })
    return result


@router.get("/{module_id}")
async def get_module_scenarios(
    module_id: str,
    module_loader: ModuleLoader = Depends(get_module_loader),
):
    """
    Return all scenarios for a module.
    Returns: [ { id: str, title: str } ]
    """
    scenario_ids = module_loader.list_scenarios(module_id)
    if not scenario_ids:
        return []
    return [
        module_loader.get_scenario_info(module_id, sid)
        for sid in scenario_ids
    ]
