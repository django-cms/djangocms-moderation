import diff from 'htmldiff';
import $ from 'jquery';
import srcDoc from 'srcdoc-polyfill';

global.prettydiff = {
    pd: {},
};

var prettydiff = require('./prettydiff').default;

/**
 * closeDropdown
 *
 * @public
 * @param {jQuery} el
 */
function closeDropdown(el) {
    el.closest('.cms-dropdown-open').find('.cms-dropdown-toggle').trigger('pointerup');
}

/**
 * getCurrentMarkup
 *
 * @public
 * @returns {String} html
 */
function getCurrentMarkup() {
    return $.ajax({
        url: window.location.href,
    }).then(markup => {
        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        $(newDoc).find('#cms-top, [data-cms], template.cms-plugin, .cms-placeholder').remove();

        // TODO don't remove all scripts, only cms/addon specific
        $(newDoc).find('script').remove();
        return newDoc.documentElement.outerHTML;
    });
}

/**
 * getPublishedMarkup
 *
 * @public
 * @returns {String} html
 */
function getPublishedMarkup() {
    return $.ajax({
        url: window.location.pathname + '?toolbar_off',
    }).then(markup => markup);
}

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
const preventScrolling = () => $('html').addClass('cms-overflow'); // TODO this should be context dependent
const allowScrolling = () => $('html').removeClass('cms-overflow');

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
        const result = diff(published, current, 'diff');
        const frame = getOrAddFrame();

        showControls();
        preventScrolling();
        srcDoc.set(frame, result);
    });
};

const showSource = () => {
    loadMarkup().then(([current, published]) => {
        const frame = getOrAddFrame();
        const markup = prettydiff.prettydiff({
            source: published,
            diff: current,
            diffview: 'inline',
            sourcelabel: 'Published',
            difflabel: 'Current',
            html: true,
            wrap: 80,
        });

        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        // TODO fix paths
        $(newDoc).find('head').append(`
            <link rel="stylesheet" href="/static/djangocms_moderation/css/source.css" type="text/css">
            <script src="/static/djangocms_moderation/js/libs/api/dom.js"></script>
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
        const button = $(e.currentTarget);

        if (button.is('.cms-btn-active')) {
            return;
        }

        $('.js-cms-moderation-control').removeClass('cms-btn-active');
        button.addClass('cms-btn-active');
        e.preventDefault();
        showSource();
    });
};

$(function() {
    addControls();
    $('.js-cms-moderation-view-diff').on('click', e => {
        e.preventDefault();

        closeDropdown($(e.target));

        CMS.API.Toolbar.showLoader();

        showVisual();
    });
});
