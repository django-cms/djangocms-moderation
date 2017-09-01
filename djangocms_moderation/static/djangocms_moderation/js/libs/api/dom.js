(function dom__init() {
    "use strict";

    //namespace to test for web browser features for progressive enhancement
    //namespace for event handlers
    var event            = {
        //allows visual folding of consecutive equal lines in a diff report
        difffold     : function dom__event_difffold() {
            var a         = 0,
                b         = 0,
                self      = this,
                title     = self
                    .getAttribute("title")
                    .split("line "),
                min       = Number(title[1].substr(0, title[1].indexOf(" "))),
                max       = Number(title[2]),
                inner     = self.innerHTML,
                lists     = [],
                parent    = self.parentNode.parentNode,
                listnodes = (parent.getAttribute("class") === "diff")
                    ? parent.getElementsByTagName("ol")
                    : parent
                        .parentNode
                        .getElementsByTagName("ol"),
                listLen   = listnodes.length;
            for (a = 0; a < listLen; a = a + 1) {
                lists.push(listnodes[a].getElementsByTagName("li"));
            }
            max = (max >= lists[0].length)
                ? lists[0].length
                : max;
            if (inner.charAt(0) === "-") {
                self.innerHTML = "+" + inner.substr(1);
                for (a = min; a < max; a = a + 1) {
                    for (b = 0; b < listLen; b = b + 1) {
                        lists[b][a].style.display = "none";
                    }
                }
            } else {
                self.innerHTML = "-" + inner.substr(1);
                for (a = min; a < max; a = a + 1) {
                    for (b = 0; b < listLen; b = b + 1) {
                        lists[b][a].style.display = "block";
                    }
                }
            }
        }
    };

    //alter tool on page load in reflection to saved state
    var load = function dom__event_recycle_execOutput_diffList() {
        var difflist = document.getElementsByTagName("ol");
        if (!difflist.length) {
            return;
        }
        var cells = difflist[0].getElementsByTagName("li"),
            len   = cells.length,
            a     = 0;
        for (a = 0; a < len; a = a + 1) {
            if (cells[a].getAttribute("class").match(/fold/)) {
                cells[a].onclick = event.difffold;
                if (cells[a].getAttribute("class").match(/equal/)) {
                    cells[a].onclick();
                }
            }
        }


    }
    window.onload = load;
}());
