import hashlib
import tempfile

from packaging.version import parse
from pyramid_jinja2 import IJinja2Environment
from sqlalchemy.orm import joinedload

from warehouse.packaging.interfaces import ISimpleStorage
from warehouse.packaging.models import File, Release


def _simple_detail(project, request):
    # Get all of the files for this project.
    files = sorted(
        request.db.query(File)
        .options(joinedload(File.release))
        .join(Release)
        .filter(Release.project == project)
        .all(),
        key=lambda f: (parse(f.release.version), f.filename),
    )

    return {"project": project, "files": files}


def render_simple_detail(project, request, store=False):
    context = _simple_detail(project, request)

    env = request.registry.queryUtility(IJinja2Environment, name=".jinja2")
    template = env.get_template("templates/legacy/api/simple/detail.html")
    content = template.render(**context, request=request)

    content_hasher = hashlib.blake2b(digest_size=256 // 8)
    content_hasher.update(content.encode("utf-8"))
    content_hash = content_hasher.hexdigest().lower()
    simple_detail_path = f"{project.normalized_name}/{content_hash}.html"

    if store:
        storage = request.find_service(ISimpleStorage)
        with tempfile.NamedTemporaryFile() as f:
            f.write(content.encode("utf-8"))
            storage.store(
                simple_detail_path,
                f.name,
                meta={
                    "project": project.normalized_name,
                    "hash": content_hash,
                },
            )

    return (content_hash, simple_detail_path)
