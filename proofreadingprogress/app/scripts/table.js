const usp = new URLSearchParams(window.location.search);
const params = Object.fromEntries(usp.entries());
const base = `${window.location.origin}/${
    document.getElementById('prefix').innerText || ''}/api/v1`;

function openWindowWithGet(url, data, name = '', params = '') {
  var usp = new URLSearchParams(data);
  window.open(`${url}?${usp.toString()}`, name, params);
}

window.app = new Vue({
  el: '#app',
  data: {
    response: [],
    headers: [],
    selected: [],
    supportSelect: params.select || false
  },
  computed: {
    selectAll: {
      get: function() {
        return this.response ? this.selected.length == this.response.length :
                               false;
      },
      set: function(value) {
        var selected = [];

        if (value) {
          this.response.forEach(function(resp) {
            selected.push(resp[0]);
          });
        }

        this.selected = selected;
      }
    }
  },
  methods: {
    publish: function() {
      openWindowWithGet(new URL(`${base}/publish`), {
        rootid: this.selected.map(r => {
          if (r[0] == '\'' && r.length > 1) r = r.slice(1);
          return r;
        })
      });
      window.close();
    },
  }
});