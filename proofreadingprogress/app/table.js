const usp = new URLSearchParams(window.location.search);
const params = Object.fromEntries(usp.entries());

const app = new Vue({
  el: '#app',
  data: {
    response: JSON.parse(params.response) ?? [],
    headers: JSON.parse(params.headers) ?? []
  }
});