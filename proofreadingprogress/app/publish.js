const base = `${window.location.origin}/api/v1`;
const params = (new URL(document.location)).searchParams;
// const auto_rootid = params.get('rootid');
const wparams = `location=no,toolbar=no,menubar=no,width=620,left=0,top=0`;
const fly_v31 =
    `https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/`;
const fly_training_v2 =
    `https://minnie.microns-daf.com/segmentation/api/v1/table/fly_training_v2/`;

// TODO: CLEANUP
const app = new Vue({
  el: '#app',
  data: {
    published: {},
    verify: true,
    dataset:
        'https://prodv1.flywire-daf.com/segmentation/api/v1/table/fly_v31/',
    doi: '',
    pname: '',
    tag: '',
    multiqueryRaw: '',
    multiquery: [],
    failed: '',
    rawResponse: [],
    response: [],
    headers: [],
    colChoices: [],
    keyindex: 0,
    csv: '',
    userCSV: '',
    userList: {},
    userHeaders: [],
    importedCSVName: '',
    importedCSVFile: [],
    idToRowMap: {},
    numval: [{classes: 'numval', rule: /^[0-9]+$/, disableAdd: true}],
    status: 'Submit',
    loading: false
  },
  computed: {
    isReady: function() {
      return this.multiqueryRaw.length && this.validateAll() && !this.loading;
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
      return /^ *\d+ *(?:, *\d+ *)*$/gm.test(this.multiqueryRaw) ||
          !this.multiqueryRaw.length;
    },
    DOITest: function() {
      return /^10.\d{4,9}[-._;()/:A-Z0-9]+$/i.test(this.doi) ||
          !this.doi.length;
    },
    titleTest: function() {
      return /^[\w\-\s]+$/.test(this.pname) || !this.pname.length;
    },
    processMQR: function() {
      const multiquerySplit = this.multiqueryRaw.split(/[ ,]+/);
      this.multiquery =
          multiquerySplit.filter(e => e.length && !isNaN(parseInt(e)))
    },
    apiRequest: async function() {
      // Disable button, activate spinner
      this.loading = true;
      this.status = 'Loading...';
      this.processMQR();

      const request = new URL(`${base}/pub/`);
      request.searchParams.set('queries', this.multiquery.join(' '));
      request.searchParams.set('verify', this.verify);
      request.searchParams.set('doi', this.doi);
      request.searchParams.set('pname', this.pname);
      let path = new URL(this.dataset).pathname.split('/');
      path.pop();
      request.searchParams.set('dataset', path.pop());

      try {
        await this.published;
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
    generateResponse: function(segments, uids) {
      this.userHeaders =
          ['user_name', 'user_id', 'total_edits', 'contributed>10%'];
      let userList = {};
      this.response = segments.map(seg => {
        let headers = Array.from(seg.keys());
        let row = Array.from(seg.values());
        row[0] = `'${row[0]}`;  // Adds ' to front of seg id
        seg.set('contributor', []);

        let segId = seg.get('segment_ID');
        let isPublished = seg.get('published');
        // there may be a better way to sort (requires filtering)
        let contributor = Object.keys(uids)
                              .filter(a => uids[a][segId])
                              .sort(
                                  (a, b) => uids[b][segId].number_of_edits -
                                      uids[a][segId].number_of_edits);

        contributor.forEach(uid => {
          let user = uids[uid];
          let contributed = user[segId];
          let edits =
              contributed && !isPublished ? contributed.number_of_edits : 0;

          let percentEdits = percent((edits / seg.get('total_edits')));
          let contributor = new Map([
            ['user_name', user.user_name], ['user_id', uid],
            ['number_of_edits', edits], ['percent_of_total', percentEdits]
          ]);
          headers = headers.concat(Array.from(contributor.keys()));
          row = row.concat(Array.from(contributor.values()));
          seg.get('contributor').push(contributor);
          if (!userList[uid]) {
            userList[uid] = {
              user_name: user.user_name,
              user_id: uid,
              total_edits: 0,
              contributed_at_least_10Percent: 0
            };
          }
          userList[uid].total_edits += edits;
          userList[uid].contributed_at_least_10Percent +=
              ((percentEdits >= 10) ? 1 : 0);
        });
        if (this.headers.length < headers.length) {
          this.headers = headers;
        }
        return row;
      });
      const csv = [this.headers, ...this.response];
      this.csv = Papa.unparse(csv);
      this.userList = Array.from(Object.values(userList));
      this.userCSV = Papa.unparse(this.userList);
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
    viewResults: function() {
      let headers = JSON.stringify(this.headers);
      let response = JSON.stringify(this.response);
      openWindowWithGet(
          new URL(`${base}/table`), {headers, response}, `Edits Table`,
          wparams);
      /*let editTable =
          window.open(new URL(`${base}/table`), `Edits Table`, wparams);
      openWindowWithPost(new URL(`${base}/table`), {headers, response});*/
    },
    mergeCSV: function() {
      const filename = `${this.importedCSVName.name}_merged.csv`;
      const mergedCSV = [...this.importedCSVFile];
      Papa.parse(this.csv, {
        complete: (results) => {
          results.data.map((row, i) => {
            const key = i ? this.idToRowMap[row[0].slice(1)] : 0;
            const firsthalf = mergedCSV[key].slice(0, this.keyindex);
            const secondhalf = this.keyindex < mergedCSV[key].length - 1 ?
                mergedCSV[key].slice(this.keyindex + 1) :
                [];
            mergedCSV[key] = [...firsthalf, ...secondhalf, ...row];
          });

          const blob = new Blob(
              [Papa.unparse(mergedCSV)], {type: 'text/csv;charset=utf-8;'});
          const link = document.createElement('a');
          const url = URL.createObjectURL(blob);
          link.setAttribute('href', url);
          link.setAttribute('download', filename);
          link.click();
        }
      });
    },
    exportUserCSV: function() {
      const filename = 'useredits.csv';
      const blob = new Blob([this.userCSV], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    },
    viewUsers: function() {
      let headers = JSON.stringify(this.userHeaders);
      let response = JSON.stringify(this.userList.map(r => Object.values(r)));
      openWindowWithGet(
          new URL(`${base}/table`), {headers, response}, `User Table`, wparams);
      /*let userTable =
          window.open(new URL(`${base}/table`), `User Table`, wparams);
      openWindowWithPost(new URL(`${base}/table`), {headers, response});*/
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
          this.multiqueryRaw =
              this.multiqueryRaw.concat(i == 1 ? '' : ', ', e[index]);
          this.idToRowMap[e[index]] = i;
        }
      });
    }
  }
});