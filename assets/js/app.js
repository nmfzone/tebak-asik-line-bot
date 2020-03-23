import './bootstrap'
import Vue from 'vue'

window.Vue = Vue

moment.tz.setDefault('Asia/Jakarta')

const app = new Vue({
  el: '#app',
});


const textarea = $('textarea.auto-expand')

if (textarea) {
  function autoExpand() {
    this.style.cssText = 'padding:0; overflow: hidden';
    this.style.cssText = 'height:' + (this.scrollHeight + 10) + 'px'
  }

  textarea.each(autoExpand)

  textarea.on('keydown', autoExpand)
}
