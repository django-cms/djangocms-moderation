import diff from 'htmldiff';
import $ from 'jquery';
import srcDoc from 'srcdoc-polyfill';
import memoize from 'lodash.memoize';

const memoizedDiff = memoize(diff);

// eslint-disable-next-line
__webpack_public_path__ = require('./get-dist-path')('bundle.moderation');

const closeDropdown = el => {
    el.closest('.cms-dropdown-open').find('.cms-dropdown-toggle').trigger('pointerup');
};

const resetEditMode = () => {
    return $.ajax({
        url: window.location.pathname + '?edit&structure'
    });
};

const getCurrentMarkup = () => {
    return $.ajax({
        url: window.location.pathname + '?toolbar_off', // TODO respect other params
    }).then(markup => markup);
};

const getPublishedMarkup = () => {
    return $.ajax({
        url: window.location.pathname + '?toolbar_off&preview', // TODO respect other params
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
let structureBoardToggle;

const showControls = () => {
    $('.cms-moderation-controls').show();
    $('.cms-toolbar-right, .cms-toolbar-item-navigation').hide();
    structureBoardToggle = CMS.API.StructureBoard._toggleStructureBoard.bind(CMS.API.StructureBoard);
    CMS.API.StructureBoard._toggleStructureBoard = $.noop;
};
const hideControls = () => {
    $('.cms-moderation-controls').hide();
    $('.cms-toolbar-right, .cms-toolbar-item-navigation').show();
    CMS.API.StructureBoard._toggleStructureBoard = structureBoardToggle;
};

const preventScrolling = () => $('html').addClass('cms-moderation-overflow');
const allowScrolling = () => $('html').removeClass('cms-moderation-overflow');

const closeFrame = e => {
    e.preventDefault();
    CMS.API.StructureBoard._toggleStructureBoard = structureBoardToggle;
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
        // have to do them in order because the `preview` flag triggers a state,
        // so to avoid race condition we query current markup first
        p = getCurrentMarkup().then(current => {
            return getPublishedMarkup().then(published => {
                return [current, published];
            });
        }).then(r => {
            CMS.API.Toolbar.hideLoader();
            return r;
        });
    }
    return p;
};

const showVisual = () => {
    CMS.API.StructureBoard.hide();
    loadMarkup().then(([current, published]) => {
        const result = memoizedDiff(published, current, 'cms-diff');
        const frame = getOrAddFrame();

        var newDoc = new DOMParser().parseFromString(result, 'text/html');

        $(newDoc).find('body').append(`<style>${require('../css/moderation.css')}</style>`);

        showControls();
        preventScrolling();
        srcDoc.set(frame, newDoc.documentElement.outerHTML);

        resetEditMode();
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
        const markup = prettydiff.default.diff(
            published,
            current
        );

        var newDoc = new DOMParser().parseFromString(markup, 'text/html');

        $(newDoc).find('head').append(`
            <script>
                ${prettydiff.default.js}
            </script>
            <style>
                ${prettydiff.default.styles}
            </style>
        `);

        srcDoc.set(frame, newDoc.documentElement.outerHTML);
    });
};

const cancelIfLoadedInsideAnIframe = () => {
    if (window.parent && window.parent !== window) {
        window.top.location.href = window.location.href;
    }
};

const addControls = () => {
    $('#cms-top').append(`
        <div class="cms-moderation-controls" style="display: none">
            <div class="cms-tooblar-item cms-toolbar-item-buttons">
                <div class="cms-btn-group">
                    <a href="#"
                        class="cms-btn cms-btn-active js-cms-moderation-control js-cms-moderation-control-visual">
                        Visual
                    </a>
                    <a href="#" class="cms-btn js-cms-moderation-control js-cms-moderation-control-source">
                        Source
                    </a>
                </div>
            </div>
            <div class="cms-moderation-control-close">
                <a href="#" class="js-cms-moderation-close">
                    <span class="cms-icon cms-icon-close"></span>
                </a>
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
    cancelIfLoadedInsideAnIframe();
});
