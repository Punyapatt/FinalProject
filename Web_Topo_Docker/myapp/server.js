var express = require('express');
var app = express();
//var port = process.env.PORT || 7777
var port = 7777
const fs = require('fs');
const editJsonFile = require("edit-json-file");
// var jsnx = require('jsnetworkx');

let rawdata = fs.readFileSync('topology.json');
let topology = JSON.parse(rawdata);
console.log(topology)

app.use(express.static('public'));
app.use(express.json())

app.set('view engine', 'ejs')

// index page
app.get('/', function(req, res) {
    let rawdata = fs.readFileSync('topology.json');
    let topology = JSON.parse(rawdata);
    console.log(topology)

    res.render('pages/index', {
        host : rawdata,
        test : topology
    })
});
  
// about page
app.get('/about', function(req, res) {
    res.render('pages/about');
});

app.put('/topology', (req, res) => {
    var payload = req.body  
    let file = editJsonFile('topology.json')
    file.set("switch", payload.switch)
    file.set("host", payload.host)
    file.set("test", payload.test)
    file.save()
    file = editJsonFile('topology.json', {
        autosave: true
    })

    console.log(payload.test)
    res.json(payload.test)
});
  
app.listen(port, function () {
    console.log('Starting node.js on port ' + port)
});


