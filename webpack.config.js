var webpack = require('webpack');
// var path = require('path');

module.exports = function(opts) {
    'use strict';

    var PROJECT_PATH = opts.PROJECT_PATH;
    var debug = opts.debug;

    if (!debug) {
        process.env.NODE_ENV = 'production';
    }

    var baseConfig = {
        devtool: false,
        watch: !!opts.watch,
        entry: {
            // CMS frontend
            moderation: PROJECT_PATH.js + '/base.js',
        },
        output: {
            path: PROJECT_PATH.js + '/dist/',
            filename: 'bundle.[name].min.js',
            chunkFilename: 'bundle.[name].min.js',
            jsonpFunction: 'moderationWebpackJsonp',
        },
        plugins: [],
        externals: {
            jquery: 'CMS.$',
            'cms.plugins': 'CMS.Plugin',
            'cms.modal': 'CMS.Modal',
            'cms.structureboard': 'CMS.StructureBoard',
            'cms.messages': 'CMS.Messages',
        },
        resolve: {
            alias: {
                htmldiff: PROJECT_PATH.js + '/libs/htmldiff.js',
                prettydiff: PROJECT_PATH.js + '/prettydiff.js',
            },
        },
        module: {
            rules: [
                // must be first
                {
                    test: /\.js$/,
                    use: [
                        {
                            loader: 'babel-loader',
                            options: {
                                retainLines: true,
                            },
                        },
                    ],
                    exclude: /(node_modules|libs|addons\/jquery.*)/,
                },
                {
                    test: /(.html$|.css$|api\/dom)/,
                    use: [
                        {
                            loader: 'raw-loader',
                        },
                    ],
                },
            ],
        },
        stats: 'verbose',
    };

    if (debug) {
        baseConfig.devtool = 'cheap-module-eval-source-map';
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.NoEmitOnErrorsPlugin(),
            new webpack.DefinePlugin({
                __DEV__: 'true',
            }),
        ]);
    } else {
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.DefinePlugin({
                __DEV__: 'false',
            }),
            new webpack.optimize.ModuleConcatenationPlugin(),
            new webpack.optimize.UglifyJsPlugin({
                comments: false,
                compressor: {
                    drop_console: true, // eslint-disable-line
                },
            }),
        ]);
    }

    return baseConfig;
};
