/* eslint-disable no-unused-vars */
const csspretty = require('./libs/lib/csspretty.js');
const csvpretty = require('./libs/lib/csvpretty.js');
const diffview = require('./libs/lib/diffview.js');
const finalFile = require('./libs/lib/finalFile.js');
const jspretty = require('./libs/lib/jspretty.js');
const language = require('./libs/lib/language.js');
const markuppretty = require('./libs/lib/markuppretty.js');
const options = require('./libs/lib/options.js');
const safeSort = require('./libs/lib/safeSort.js');
const prettydiff = require('./libs/prettydiff.js');

global.prettydiff.csspretty = csspretty;
global.prettydiff.csvpretty = csvpretty;
global.prettydiff.diffview = diffview;
global.prettydiff.finalFile = finalFile;
global.prettydiff.jspretty = jspretty;
global.prettydiff.language = language;
global.prettydiff.markuppretty = markuppretty;
global.prettydiff.safeSort = safeSort;
global.prettydiff.prettydiff = prettydiff;

export default global.prettydiff;
