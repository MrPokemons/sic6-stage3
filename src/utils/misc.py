import secrets


def secure_shuffle(lst):
    for i in reversed(range(1, len(lst))):
        j = secrets.randbelow(i + 1)
        lst[i], lst[j] = lst[j], lst[i]
    return lst
