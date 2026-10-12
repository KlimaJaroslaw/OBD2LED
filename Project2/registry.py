PROGRAMS, SOURCES, DEVICES = {}, {}, {}

def register(table, name):
    def deco(cls):
        table[name] = cls
        return cls
    return deco