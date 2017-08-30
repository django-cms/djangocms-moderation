import diff from 'htmldiff';
import $ from 'jquery';
import srcDoc from 'srcdoc-polyfill';

// eslint-disable-next-line
__webpack_public_path__ = require('./get-dist-path')('bundle.moderation');

const closeDropdown = el => {
    el.closest('.cms-dropdown-open').find('.cms-dropdown-toggle').trigger('pointerup');
};

const getCurrentMarkup = () => {
    return $.ajax({
        url: window.location.href,
    }).then(markup => {
        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        // TODO don't remove all scripts, only cms/addon specific - will be obsolete when
        // we implement the logic of showing "draft as if it would be published"
        $(newDoc).find('#cms-top, [data-cms], template.cms-plugin, .cms-placeholder').remove();
        $(newDoc).find('script').remove();
        return newDoc.documentElement.outerHTML;
    });
};

const getPublishedMarkup = () => {
    return $.ajax({
        url: window.location.pathname + '?toolbar_off',
    }).then(markup => markup);
};

const getOrAddFrame = () => {
    let frame = $('.js-cms-moderation-diff-frame');

    if (frame.length) {
        return frame[0];
    }

    frame = $('<iframe class="js-cms-moderation-diff-frame cms-moderation-diff-frame"></iframe>');

    $('#cms-top').append(frame);

    return frame[0];
};


let p;
const showControls = () => $('.cms-moderation-controls').show();
const hideControls = () => $('.cms-moderation-controls').hide();

const preventScrolling = () => $('html').addClass('cms-moderation-overflow');
const allowScrolling = () => $('html').removeClass('cms-moderation-overflow');

const closeFrame = () => {
    hideControls();
    allowScrolling();
    $('.js-cms-moderation-control').removeClass('cms-btn-active');
    $('.js-cms-moderation-control-visual').addClass('cms-btn-active');
    $(getOrAddFrame()).remove();
    p = null;
};

const loadMarkup = () => {
    if (!p) {
        CMS.API.Toolbar.showLoader();
        p = Promise.all([getCurrentMarkup(), getPublishedMarkup()]).then(r => {
            CMS.API.Toolbar.hideLoader();
            return r;
        });
    }
    return p;
};

const showVisual = () => {
    loadMarkup().then(([current, published]) => {
        // TODO change to cms-diff
        const result = diff(published, current, 'diff');
        const frame = getOrAddFrame();

        showControls();
        preventScrolling();
        srcDoc.set(frame, result);
    });
};

const showSource = () => {
    Promise.all([
        import(
            /* webpackChunkName: "prettydiff" */
            'prettydiff'
        ),
        loadMarkup(),
    ]).then(([prettydiff, [current, published]]) => {
        const frame = getOrAddFrame();
        const markup = prettydiff.default.prettydiff({
            source: published,
            diff: current,
            diffview: 'inline',
            sourcelabel: 'Published',
            difflabel: 'Current',
            html: true,
            wrap: 80,
        });

        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        $(newDoc).find('head').append(`
            <style>
                ${prettydiff.default.styles}
            </style>
            <script>
                ${prettydiff.default.rawAPI}
            </script>
        `);

        srcDoc.set(frame, newDoc.documentElement.outerHTML);
    });
};

const addControls = () => {
    $('#cms-top').append(`
        <div class="cms-moderation-controls" style="display: none">
            <div class="cms-tooblar-item cms-toolbar-item-buttons">
                <div class="cms-moderation-history cms-btn-group">
                    <a href="#"
                        class="cms-btn cms-btn-active js-cms-moderation-control js-cms-moderation-control-visual">
                        Visual
                    </a>
                    <a href="#" class="cms-btn js-cms-moderation-control js-cms-moderation-control-source">
                        Source
                    </a>
                    <a href="#" class="cms-btn js-cms-moderation-close">
                        <span class="cms-icon cms-icon-close"></span>
                    </a>
                </div>
            </div>
        </div>
    `);

    $('.js-cms-moderation-close').on('click', closeFrame);
    $('.js-cms-moderation-control-visual').on('click', e => {
        e.preventDefault();
        const button = $(e.currentTarget);

        if (button.is('.cms-btn-active')) {
            return;
        }

        $('.js-cms-moderation-control').removeClass('cms-btn-active');
        button.addClass('cms-btn-active');

        showVisual();
    });

    $('.js-cms-moderation-control-source').on('click', e => {
        e.preventDefault();
        const button = $(e.currentTarget);

        if (button.is('.cms-btn-active')) {
            return;
        }

        $('.js-cms-moderation-control').removeClass('cms-btn-active');
        button.addClass('cms-btn-active');

        showSource();
    });

    $('.js-cms-moderation-view-diff').on('click', e => {
        e.preventDefault();
        closeDropdown($(e.target));
        showVisual();
    });
};

$(function() {
    addControls();
});
