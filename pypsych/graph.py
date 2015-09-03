from hashlib import md5 as hash
from time import time

class Node:
    def __init__(self):
        pass

class Edge:
    def __init__(self, a, b):
        self.left = a
        self.right = b

class Group:
    def __init__(self, members):
        self.members = members

class ViewResults:
    def __init__(self, data):
        self.data = data
        self.filtered_data = data
        self.position = 0
        self.length_lock = None #prevent length checking while filtering.
    def __iter__(self):
        return self.filtered_data.__iter__()
    def filter(self, filt):
        self.filtered_data = filter(filt, self.data)
    def sort(self, func, reverse=False):
        self.data.sort(key=func, reverse=reverse)

class View:
    def __init__(self):
        pass
    def map(self, document):
        pass
    def reduce(self, results):
        return results

class Database:
    def __init__(self, storage):
        self.storage = storage
        self.views = {}
    def register_view(self, name, view):
        self.storage.introduce_view(name)
        self.views[name.lower()] = view
    def query_view(self, name):
        return ViewResults(self.storage.view_results(name))
    def write(self, doc, id=None):
        if id:
            self.storage.update_document(id, doc)
        else:
            id = self.storage.create_document(doc)
        doc = self.storage.get_document(id)
        for name, v in self.views.items():
            result = v.map(doc)
            if result:
                self.storage.add_map_result(name, id, result)
                total_results = self.storage.map_results(name)
                self.storage.store_reduced_results(name, v.reduce(list(total_results.values())))
        return id

class Storage:
    def __init__(self):
        self.documents = {}
        self.view_storage = {}
    def get_document(self, id):
        return self.documents[id]
    def update_document(self, id, doc):
        self.documents[id] = {
            '__id__':self.documents[id]['__id__'],
            'modified':time(),
            'created':self.documents[id]['created'],
            'doc':doc
        }
    def introduce_view(self, name):
        self.view_storage[name] = {
            "map":{},
            "reduced":[]
        }
    def create_document(self, doc):
        id = self.create_id(doc)
        t = time()
        self.documents[id] = {
            '__id__':id,
            'modified':t,
            'created':t,
            'doc':doc
        }
        return id
    def create_id(self, doc):
        h = hash()
        h.update(str(doc).encode('utf-8'))
        return h.hexdigest()
    def add_map_result(self, viewname, docid, result):
        if viewname not in self.view_storage:
            self.view_storage[viewname] = {
                'map':{
                    docid: result
                },
                'reduced':[]
            }
        else:
            self.view_storage[viewname]['map'][docid] = result
    def store_reduced_results(self, viewname, results):
        if viewname not in self.view_storage:
            self.view_storage[viewname] = {
                'map':{},
                'reduced': results
            }
        else:
            self.view_storage[viewname]['reduced'] = results
    def map_results(self, viewname):
        return self.view_storage[viewname]['map']
    def view_results(self, viewname):
        return self.view_storage[viewname]['reduced']
