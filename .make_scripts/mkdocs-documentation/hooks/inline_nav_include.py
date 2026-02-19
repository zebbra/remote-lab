from pathlib import Path
from urllib.parse import urlparse

import yaml


INCLUDE_PREFIX = "!include"


def on_config(config):
    nav = config.get("nav")
    if not nav:
        return config

    config_path = Path(config.get("config_file_path", "mkdocs.yml")).resolve()
    project_root = config_path.parent
    root_docs_dir = config.get("docs_dir", "docs")
    root_docs_path = (project_root / root_docs_dir).resolve()

    include_cache = {}
    config["nav"] = _replace_includes(
        nav,
        project_root,
        root_docs_path,
        include_cache,
    )
    return config


def _replace_includes(node, project_root, root_docs_path, include_cache):
    if isinstance(node, list):
        new_list = []
        for item in node:
            include_nav = _load_include_nav(item, project_root, root_docs_path, include_cache)
            if include_nav is not None:
                if isinstance(include_nav, list):
                    new_list.extend(include_nav)
                else:
                    new_list.append(include_nav)
            else:
                new_list.append(
                    _replace_includes(item, project_root, root_docs_path, include_cache)
                )
        return new_list
    if isinstance(node, dict):
        new_dict = {}
        for key, value in node.items():
            include_nav = _load_include_nav(value, project_root, root_docs_path, include_cache)
            if include_nav is not None:
                new_dict[key] = include_nav
            else:
                new_dict[key] = _replace_includes(
                    value, project_root, root_docs_path, include_cache
                )
        return new_dict
    return node


def _rewrite_nav_paths(node, include_docs_path, root_docs_path):
    if isinstance(node, list):
        return [_rewrite_nav_paths(item, include_docs_path, root_docs_path) for item in node]
    if isinstance(node, dict):
        return {
            key: _rewrite_nav_paths(value, include_docs_path, root_docs_path)
            for key, value in node.items()
        }
    if isinstance(node, str):
        return _rewrite_path(node, include_docs_path, root_docs_path)
    return node


def _rewrite_path(path_value, include_docs_path, root_docs_path):
    if _is_external_path(path_value):
        return path_value

    path_part, sep, anchor = path_value.partition("#")
    if not path_part or path_part.startswith("/"):
        return path_value

    abs_path = (include_docs_path / path_part).resolve()
    try:
        rel_path = str(abs_path.relative_to(root_docs_path))
    except ValueError:
        rel_path = str(abs_path)
    if sep:
        return f"{rel_path}#{anchor}"
    return rel_path


def _is_external_path(path_value):
    if path_value.startswith(("#", "mailto:")):
        return True
    parsed = urlparse(path_value)
    return bool(parsed.scheme and parsed.netloc)


def _load_include_nav(value, project_root, root_docs_path, include_cache):
    if not isinstance(value, str):
        return None
    token = value.strip()
    if not token.startswith(INCLUDE_PREFIX):
        return None

    _, _, include_target = token.partition(" ")
    include_target = include_target.strip()
    if not include_target:
        return None

    include_path = (project_root / include_target).resolve()
    if include_path in include_cache:
        return include_cache[include_path]

    if not include_path.exists():
        print(f"[inline-nav-include] Missing include: {include_path}")
        include_cache[include_path] = None
        return None

    include_config = yaml.safe_load(include_path.read_text()) or {}
    include_nav = include_config.get("nav")
    if not include_nav:
        print(f"[inline-nav-include] No nav found in: {include_path}")
        include_cache[include_path] = None
        return None

    include_docs_dir = include_config.get("docs_dir", "docs")
    include_docs_path = (include_path.parent / include_docs_dir).resolve()

    rewritten_nav = _rewrite_nav_paths(include_nav, include_docs_path, root_docs_path)
    include_cache[include_path] = rewritten_nav
    return rewritten_nav
