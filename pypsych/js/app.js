(function () {

    function Router() {
        this.routes = {};
        return this;
    }

    Router.prototype.install_route = (function (route, callback) {
        this.routes[route] = callback;
    });

    Router.prototype.connect_signals = (function (x) {
        x.addEventListener("popstate", this.route);
    });

    Router.prototype.route = (function (evnt) {
        var path = document.location.pathname;
        if (path in this.routes) {
            this.routes[path]();
        }
    });

    Router.prototype.go = (function (path, title) {
        window.history.pushState(null, title, path);
        this.route(null);
    });

    function TemplateManager() {
        this.loaded_templates = {};
        return this;
    }

    TemplateManager.prototype.get_template = (function (name, cb) {
        if (name in this.loaded_templates) {
            cb(this.loaded_templates);
        } else {
            this.download_template(name, (function (t) {
                this.loaded_templates[name] = t;
                cb(t);
            }).bind(this));
        }
    });

    TemplateManager.prototype.download_template = (function (name, cb) {
        var ajx = new XMLHttpRequest();
        ajx.open("GET", "/template/" + name);
        ajx.onreadystatechange = (function () {
            if (ajx.readyState == 4 && ajx.status == 200) {
                cb(ajx.responseText);
            }
        });
        ajx.send();
    });

    TemplateManager.prototype.render = (function (base, template, data, cb) {
        this.get_template(template, (function (template) {
            base.innerHTML = Mustache.render(template, data);
        }).bind(this));
    });

    var router = new Router();

    router.install_route("/", (function () {
    }));

    router.install_route("/durp", (function () {
    }));

    router.connect_signals(window);

    router.route(null);

    document.addEventListener("readystatechange", (function () {
        if (document.readyState === "interactive") {
            var tm = new TemplateManager();
            tm.render(document.querySelector("#frame_area"), "home", {
                name: "Tyler"
            }, null);
        }
    }));

})();