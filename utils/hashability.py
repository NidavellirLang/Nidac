def ishashable(obj):
    try:
        hash(obj)
    except TypeError:
        return False
    return True
