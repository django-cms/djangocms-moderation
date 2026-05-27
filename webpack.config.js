const path = require('path');
const webpack = require('webpack');

const PROJECT_ROOT = path.resolve(__dirname, 'djangocms_moderation/static/djangocms_moderation');
const PROJECT_PATH = {
    js: path.join(PROJECT_ROOT, 'js'),
    sass: path.join(PROJECT_ROOT, 'sass'),
    css: path.join(PROJECT_ROOT, 'css'),
};

module.exports = (_env, argv = {}) => {
    const isProduction = argv.mode !== 'development';

    return {
        mode: isProduction ? 'production' : 'development',
        devtool: isProduction ? false : 'eval-cheap-module-source-map',
        entry: {
            moderation: path.join(PROJECT_PATH.js, 'base.js'),
        },
        output: {
            path: path.join(PROJECT_PATH.js, 'dist'),
            filename: 'bundle.[name].min.js',
            chunkFilename: 'bundle.[name].min.js',
            chunkLoadingGlobal: 'moderationWebpackJsonp',
        },
        externals: {
            jquery: 'CMS.$',
            'cms.plugins': 'CMS.Plugin',
            'cms.modal': 'CMS.Modal',
            'cms.structureboard': 'CMS.StructureBoard',
            'cms.messages': 'CMS.Messages',
        },
        resolve: {
            alias: {
                htmldiff: path.join(PROJECT_PATH.js, 'libs/htmldiff.js'),
                prettydiff: path.join(PROJECT_PATH.js, 'prettydiff.js'),
            },
        },
        module: {
            rules: [
                {
                    test: /\.js$/,
                    exclude: /(node_modules|libs|tidy|addons\/jquery.*)/,
                    use: [
                        {
                            loader: 'babel-loader',
                            options: {
                                retainLines: true,
                            },
                        },
                    ],
                },
                {
                    test: /(\.html$|api\/dom)/,
                    type: 'asset/source',
                },
                {
                    test: /\.css$/,
                    type: 'asset/source',
                    use: [
                        {
                            loader: 'postcss-loader',
                            options: {
                                postcssOptions: {
                                    plugins: [
                                        require('autoprefixer')(),
                                        require('cssnano')(),
                                    ],
                                },
                            },
                        },
                    ],
                },
            ],
        },
        plugins: [
            new webpack.DefinePlugin({
                __DEV__: JSON.stringify(!isProduction),
            }),
        ],
        stats: 'minimal',
    };
};
