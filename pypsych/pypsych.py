import bottle
from itertools import combinations, starmap
from graph import Storage, View, Database

class UserView(View):
    def map(self,doc):
        if doc['doc'].get("kind")=='user':# and doc['doc'].get("verified"):
            return doc
    def reduce(self,docs):
        return docs

class MatchesView(UserView):
    def reduce(self,docs):
        f = lambda pair:pair[2]["overall"] >= max(pair[0]['doc']["match_requirement"],pair[1]['doc']["match_requirement"])
        return list(starmap(self.make_match,filter(f,starmap(self.score,combinations(docs,2)))))
    def score(self,a,b):
        score = {
            "aspects":{
                "test_property":1
            }
        }
        score["overall"] = sum(score["aspects"].values())
        return (a,b,score)
    def make_match(self,a,b,score):
        return [a['__id__'],b['__id__'],score]

class MessageView(View):
    def map(self,doc):
        return doc if doc.get("kind")=='msg' else None
    def reduce(self,docs):
        return docs

class WebApp:
    def __init__(self,db):
        self.db = db
        self.db.register_view("users",UserView())
        self.db.register_view("matches",MatchesView())
        self.db.register_view("messages",MessageView())
    def user_exists(self,uid):
        for user in self.db.query_view("users"):
            if user['__id__']==uid:
                return True
        return False
    def create_user(self,userinfo):
        userinfo["email"] = userinfo["email"].lower()
        for user in self.db.query_view("users"):
            assert user["doc"]["email"]!=userinfo["email"]
        userinfo["verified"]=False
        userinfo['kind'] = 'user'
        userinfo["match_requirement"] = 1
        return self.db.write(userinfo)
    def send_message(self,sender,receiver,content):
        if self.user_exists(sender) and self.user_exists(receiver):
            self.db.write({
                "content":content,
                "sender":sender,
                "receiver":receiver
            })
    def run_match_search(self,uid,filts=None,sorts=None):
        base = self.db.query_view("matches")
        base.filter(lambda match:match[0]==uid or match[1]==uid)
        for f in (filts or []):
            base.filter(f)
        for s in (sorts or []):
            base.sort(s)
        yield from base
    def is_ajax(self,req):
        return True
    def respond_to_index(self,req):
        return "INDEX"
    def get_user_data(self,uid):
        #uid = req.query.get("uid")
        assert self.user_exists(uid)
        base = self.db.query_view("users")
        base.filter(lambda u:u['__id__']==uid)
        base = list(base)
        assert len(base) > 0
        return base[0]
    def respond_to_user(self,req):
        if self.is_ajax(req):
            if req.method=="GET":#get existing data.
                return self.get_user_data(req.query["uid"])
            if req.method=="POST":#create new user.
                return self.create_user(req.query)
            if req.method=="DELETE":#delete a user.
                if False:
                    self.db.destroy(req.query["uid"])
            if req.method=="PUT":
                self.db.write(req.query,req.query["uid"])

if __name__ == "__main__":
    app = WebApp(Database(Storage()))
    tid = app.create_user({
        "email":"tyler9725@gmail.com",
        "username":"tyler.elric",
        "hobbies":["lol"],
    })
    app.create_user({
        "email":"xlahr@facebook.com",
        "username":"firagastorm",
        "hobbies":["lol"]
    })
    for match in app.db.query_view("matches"):
        a = app.get_user_data(match[0])
        b = app.get_user_data(match[1])
        print(a["doc"]["username"],"and",b["doc"]["username"])