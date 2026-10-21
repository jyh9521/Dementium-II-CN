"""Hard preservation gate for source artwork with unverified or illegible text."""
import hashlib


def validate_configuration(zar, config):
    policy=config.get('preserve_original_images',{})
    replaced={r['resource'] for r in config['images']}
    conflicts=replaced & policy.keys()
    if conflicts:
        raise ValueError('Protected source image replacement rejected: '+', '.join(sorted(conflicts)))
    for name,rule in policy.items():
        if hashlib.sha256(zar.read(name)).hexdigest()!=rule['source_sha256']:
            raise ValueError('Protected source image hash mismatch: '+name)
    return len(policy)


def verify_archive(original, modified, config):
    validate_configuration(original,config)
    checked=[]
    for name,rule in config.get('preserve_original_images',{}).items():
        a,b=original.read(name),modified.read(name)
        if a!=b:
            raise ValueError('Protected original image was changed: '+name)
        checked.append(dict(resource=name,sha256=rule['source_sha256'],result='BYTE_IDENTICAL'))
    return checked
