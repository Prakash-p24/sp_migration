def test_project_scaffold_imports():
    """Basic smoke test for the project package layout."""
    import src.parsers.base_parser  # noqa: F401
    import src.ir.procedure  # noqa: F401


def test_main_is_the_migration_service_without_auth_routes():
    from src.main import app

    assert app.title == "Stored Procedure Migration"

    paths = {route.path for route in app.routes}
    assert "/health_check" in paths
    assert not paths.intersection({"/login", "/register", "/auth"})
