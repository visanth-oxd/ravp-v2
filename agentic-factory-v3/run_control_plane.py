#!/usr/bin/env python3
"""
Run script for control-plane API.

Handles the hyphenated directory name issue by setting up package structure.
"""

import sys
from pathlib import Path
import importlib.util
import types

# Add parent directory to path
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))

# Import uvicorn
import uvicorn

if __name__ == "__main__":
    # Set up package structure so relative imports work
    # Create fake package modules for control_plane.api.routes
    control_plane_pkg = types.ModuleType("control_plane")
    control_plane_pkg.__package__ = "control_plane"
    control_plane_api_pkg = types.ModuleType("control_plane.api")
    control_plane_api_pkg.__package__ = "control_plane.api"
    control_plane_api_routes_pkg = types.ModuleType("control_plane.api.routes")
    control_plane_api_routes_pkg.__package__ = "control_plane.api.routes"
    
    sys.modules["control_plane"] = control_plane_pkg
    sys.modules["control_plane.api"] = control_plane_api_pkg
    sys.modules["control_plane.api.routes"] = control_plane_api_routes_pkg
    
    # Load routes modules first (they use relative imports)
    # Load auth first since admin_tools and admin_policies depend on it
    routes_dir = repo_root / "control-plane" / "api" / "routes"
    route_modules = ["agents", "audit", "kill_switch", "policies", "tools", "auth", "admin_tools", "admin_policies", "admin_agents", "deployments", "docker_build", "gke_deploy", "a2a", "mesh", "models", "code_gen"]
    for route_name in route_modules:
        route_file = routes_dir / f"{route_name}.py"
        if route_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(f"control_plane.api.routes.{route_name}", route_file)
                if spec and spec.loader:
                    route_mod = importlib.util.module_from_spec(spec)
                    route_mod.__package__ = "control_plane.api.routes"
                    route_mod.__name__ = f"control_plane.api.routes.{route_name}"
                    sys.modules[f"control_plane.api.routes.{route_name}"] = route_mod
                    spec.loader.exec_module(route_mod)
                    setattr(control_plane_api_routes_pkg, route_name, route_mod)
                    print(f"✓ Loaded route: {route_name}")
                else:
                    print(f"⚠ Warning: Could not create spec for {route_name}")
            except Exception as e:
                print(f"✗ Error loading route {route_name}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠ Warning: Route file not found: {route_file}")
    
    # Now load main.py (it can use relative imports)
    main_py = repo_root / "control-plane" / "api" / "main.py"
    spec = importlib.util.spec_from_file_location("control_plane.api.main", main_py)
    if spec and spec.loader:
        main_mod = importlib.util.module_from_spec(spec)
        main_mod.__package__ = "control_plane.api"
        main_mod.__name__ = "control_plane.api.main"
        sys.modules["control_plane.api.main"] = main_mod
        spec.loader.exec_module(main_mod)
        app = main_mod.app
    else:
        raise ImportError("Could not load main.py")
    
    # Run uvicorn (HTTPS if SSL_KEYFILE and SSL_CERTFILE are set)
    import os
    port = int(os.getenv("PORT", "8010"))
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    ssl_certfile = os.getenv("SSL_CERTFILE")
    use_https = ssl_keyfile and ssl_certfile
    scheme = "https" if use_https else "http"
    print(f"Starting control-plane API on {scheme}://0.0.0.0:{port}")
    if use_https:
        print("TLS: SSL_KEYFILE and SSL_CERTFILE set – serving HTTPS")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print("Examples: PORT=8011 python run_control_plane.py")
    print("          SSL_KEYFILE=key.pem SSL_CERTFILE=cert.pem python run_control_plane.py  # HTTPS")
    print("=" * 60)
    kwargs = {"host": "0.0.0.0", "port": port, "log_level": "info"}
    if use_https:
        kwargs["ssl_keyfile"] = ssl_keyfile
        kwargs["ssl_certfile"] = ssl_certfile
    uvicorn.run(app, **kwargs)
