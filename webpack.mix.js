const mix = require('laravel-mix')
require('./webpack.config')
require('laravel-mix-purgecss')
require('laravel-mix-copy-watched')
require('laravel-mix-tailwind')


/*
 |--------------------------------------------------------------------------
 | Mix Asset Management
 |--------------------------------------------------------------------------
 |
 | Mix provides a clean, fluent API for defining some Webpack build steps
 | for your application.
 |
 */

mix.sass('assets/sass/app.scss', 'css')
   .sass('assets/sass/dashboard.scss', 'css')
   .js('assets/js/app.js', 'js')
   .js('assets/js/dashboard.js', 'js')
   .tailwind('./tailwind.config.js')

mix.extract(['jquery'], 'js/vendor/jquery.js')
   .extract(['vue'], 'js/vendor/vue.js')
   .extract([
     'axios',
     'lodash',
     'moment',
     'moment-timezone',
     'moment/locale/id'
   ], 'js/vendor/common.js')

mix.browserSync({
    proxy: process.env.APP_URL,
    files: ['./']
  })
  .purgeCss({
    globs: [
      './assets/js/*.js',
      './assets/js/*.jsx',
      './assets/js/*.vue',
      './**/*.html',
      './**/*.py'
    ],
    whitelistPatterns: [
      /-active$/,
      /-enter$/,
      /-leave-to$/
    ]
  })

if (mix.inProduction()) {
  mix.version()
}
