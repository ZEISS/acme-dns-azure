from copy import deepcopy


class Context:
    def copy(self):
        obj = type(self).__new__(self.__class__)
        obj.__dict__.update(self.__dict__)
        if "config" in obj.__dict__:
            obj.__dict__["config"] = deepcopy(self.__dict__["config"])
        return obj
