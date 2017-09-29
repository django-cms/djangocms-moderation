// import rawAPI from './libs/api/dom';
import styles from '../css/source.css';
import diffview from './libs/diffview';
import difflib from './libs/difflib';
import js from './libs/api/dom';
import memoize from 'lodash.memoize';

const buildView = memoize(diffview.buildView);

/**
 * Returns markup of a diff view
 *
 * @public
 * @param {String} before
 * @param {String} after
 * @returns {String}
 */
function diff(before, after) {
    const beforeLines = difflib.stringAsLines(before);
    const afterLines = difflib.stringAsLines(after);
    const sm = new difflib.SequenceMatcher(beforeLines, afterLines);
    const opcodes = sm.get_opcodes();

    return buildView({
        baseTextLines: beforeLines,
        newTextLines: afterLines,
        opcodes: opcodes,
        baseTextName: 'Published',
        newTextName: 'Current',
        contextSize: null,
        viewType: 0
    }).outerHTML;
}

export default {
    diff,
    styles,
    js
};
