const base = `${window.location.origin}/api/v1`;
const params = (new URL(document.location)).searchParams;
const wparams = `location=no,toolbar=no,menubar=no,width=620,left=0,top=0`;
const fly_v31 =
    `https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/`;
const fly_training_v2 =
    `https://minnie.microns-daf.com/segmentation/api/v1/table/fly_training_v2/`;

const app = new Vue({
  el: '#app',
  data: {
    // INPUT
    dataset: fly_v31,
    doi: '',
    pname: '',
    str_rootids: '',
    // OUTPUT
    response: [],
    headers: [],
    csv: '',
    // IMPORT
    colChoices: [],
    keyindex: 0,
    importedCSVName: '',
    importedCSVFile: [],
    idToRowMap: {},
    status: 'Submit',
    loading: false
  },
  computed: {
    isReady: function() {
      return this.str_rootids.length && this.validateAll() && !this.loading;
    },
    customDataset: function() {
      return [fly_v31, fly_training_v2].includes(this.dataset);
    },
    validRoots: function() {
      const valid = this.rootsIDTest();
      return {
        'form-error': !valid, valid
      }
    },
    validDOI: function() {
      const valid = this.DOITest();
      return {
        'form-error': !valid, valid
      }
    },
    validTitle: function() {
      const valid = this.titleTest();
      return {
        'form-error': !valid, valid
      }
    }
  },
  methods: {
    validateAll: function() {
      return this.rootsIDTest() && this.DOITest() && this.titleTest();
    },
    rootsIDTest: function() {
      return /^ *\d+ *(?:, *\d+ *)*$/gm.test(this.str_rootids) ||
          !this.str_rootids.length;
    },
    DOITest: function() {
      return /^10.\d{4,9}[-._;()/:A-Z0-9]+$/i.test(this.doi) ||
          !this.doi.length;
    },
    titleTest: function() {
      return /^[\w\-\s]+$/.test(this.pname) || !this.pname.length;
    },
    apiRequest: async function() {
      // Disable button, activate spinner
      this.loading = true;
      this.status = 'Loading...';
      this.processMQR();

      const request = new URL(`${base}/pub/`);
      request.searchParams.set('queries', this.str_rootids);
      request.searchParams.set('verify', this.verify);
      request.searchParams.set('doi', this.doi);
      request.searchParams.set('pname', this.pname);
      let path = new URL(this.dataset).pathname.split('/');
      path.pop();
      request.searchParams.set('dataset', path.pop());

      try {
        const response = await fetch(request);
        await this.processData(await response.json());
        this.status = 'Submit';
        this.loading = false;
      } catch (e) {
        alert(e);
        this.loading = false;
        this.status = 'Submit';
        throw e;
      }
    },
    processData: function(response) {
      this.queryProcess(response);
    },
    queryProcess: function(data) {
      let rows = Object.values(data);
      rows.forEach(f => {
        if (this.headers.length == 0) {
          this.headers = Object.keys(f);
        }
        this.response = [...this.response, Object.values(f)];
      });
    },
    exportCSV: function() {
      const filename = 'edits.csv';
      const blob = new Blob([this.csv], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    },
    importCSV: function(e) {
      Papa.parse(e.target.files[0], {
        skipEmptyLines: true,
        complete: (results) => {
          this.importedCSVName = e.target.files[0];
          this.importedCSVFile = results.data;
          this.colChoices = results.data[0];
        }
      });
    },
    chooseCSV: function() {
      document.getElementById('import').click();
    },
    importCol: function(index) {
      this.importedCSVFile.forEach((e, i) => {
        this.keyindex = index;
        if (i) {
          this.str_rootids =
              this.str_rootids.concat(i == 1 ? '' : ', ', e[index]);
          this.idToRowMap[e[index]] = i;
        }
      });
    }
  }
});