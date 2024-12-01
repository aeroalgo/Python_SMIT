from app import model

# todo либо проверить и дополнить маппинг дефолт префиксов к моделям либо сделать по другому

# todo поискать расхождения со старыми схемами
straight_model_map = {
    # "prefix": {"model": "model", "filter": "filter"},
    "sessions": {"model": model.Sessions, "filter": "filter"},
    "user": {"model": model.User, "filter": "filter"},
    "cargo_insurance": {"model": model.CargoInsurance, "filter": "filter"},
    "changed_by": {"model": model.User, "filter": "filter"},
}
reversed_model_map = {
    value["model"].__name__: key for key, value in straight_model_map.items()
}
