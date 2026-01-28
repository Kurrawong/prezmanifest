from pathlib import Path
import os


p1 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/unknown-class.ttl")
p2 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/sub/unknown-class.ttl")
p3 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/sub/bob/unknown-class.ttl")

p10 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/instance-manifest.ttl")
p11 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/sub/instance-manifest.ttl")
p12 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/sub/subsub/instance-manifest.ttl")
p13 = Path("/Users/nick/work/kurrawong/prez-manifest/tests/utils/main-entity-tests/sub/subsub/subsub/instance-manifest.ttl")

# os.path.commonpath([artifact.parent, manifest_root]

relative = os.path.relpath(
    p3,
    start=os.path.dirname(p11)
)

print(relative)