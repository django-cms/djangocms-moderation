(function dom__init() {
    'use strict';

    var MIN_ROWS_TO_HIDE = 5;
    var nextUntil = function nextUntil(element, predicate) {
        var next = [];
        var el = element;

        while (el.nextSibling && !predicate(el.nextSibling)) {
            el = el.nextSibling;
            next.push(el);
        }

        return next;
    };

    // namespace to test for web browser features for progressive enhancement
    // namespace for event handlers
    var event = {
        // allows visual folding of consecutive equal lines in a diff report
        difffold: function dom__event_difffold() {
            var row = this.parentNode;
            var rows;

            if (row.classList.contains('folded')) {
                row.classList.remove('folded');
                this.textContent = this.textContent.replace('+', '-');

                rows = nextUntil(row, function(r) {
                    if (r.style.display === 'none') {
                        return false;
                    }
                    return true;
                });

                rows.forEach(function(r) {
                    r.style.display = 'table-row';
                });
            } else {
                row.classList.add('folded');
                this.textContent = this.textContent.replace('-', '+');

                rows = nextUntil(row, function(r) {
                    var ths = r.getElementsByTagName('th');

                    if (ths && ths.length) {
                        var cls = ths[0].className;

                        if (cls && !cls.match('equal')) {
                            return true;
                        }
                    }

                    return false;
                });

                rows.forEach(function(r) {
                    r.style.display = 'none';
                });
            }
        }
    };

    // alter tool on page load in reflection to saved state
    var load = function () {
        var difflist = document.getElementsByTagName('table');

        if (!difflist.length) {
            return;
        }
        var cells = difflist[0].getElementsByTagName('th');
        var len = cells.length;
        var a = 0;

        for (a = 0; a < len; a += 1) {
            if (cells[a].getAttribute('class') && cells[a].getAttribute('class').match(/fold/)) {
                cells[a].onclick = event.difffold;
                if (cells[a].getAttribute('class').match(/equal/)) {
                    var rows = nextUntil(cells[a].parentNode, function(r) {
                        var ths = r.getElementsByTagName('th');

                        if (ths && ths.length) {
                            var cls = ths[0].className;

                            if (cls && !cls.match('equal')) {
                                return true;
                            }
                        }

                        return false;
                    });

                    if (rows.length > MIN_ROWS_TO_HIDE) {
                        cells[a].onclick();
                    } else {
                        cells[a].classList.remove('fold');
                        cells[a].textContent = cells[a].textContent.replace('- ', '');
                    }
                }
            }
        }
    };

    window.onload = load;
})();
