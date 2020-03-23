import $ from 'jquery'
import Axios from 'axios'
import Lodash from 'lodash'
import Moment from 'moment'
import 'moment-timezone'
import 'moment/locale/id'


window._ = Lodash

window.$ = window.jQuery = $
window.moment = Moment

window.axios = Axios

window.axios.defaults.headers.common = {
  'X-CSRF-TOKEN': window.App.csrfToken,
  'X-Requested-With': 'XMLHttpRequest',
}
