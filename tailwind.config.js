const plugin = require('tailwindcss/plugin')

module.exports = {
  theme: {
    extend: {
      fontFamily: {
        body: [
          'Lato',
          'Arial',
          'sans-serif',
        ]
      },
      fontSize: {
        md: '0.925rem',
      }
    },
  },
  variants: {
    textColor: ['important'],
  },
  plugins: [
    plugin(function({ addVariant }) {
      addVariant('important', ({ container }) => {
        container.walkRules(rule => {
          rule.selector = `.${rule.selector.slice(1)}-impt`
          rule.walkDecls(decl => {
            decl.important = true
          })
        })
      })
    })
  ],
}
