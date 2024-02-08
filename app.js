const express = require('express')
const app = express()
const port = 3000

const csv = require('csv-parser')
const fs = require('fs')

const fileUpload = require('express-fileupload');
app.use(fileUpload());

const model = {};

fs.createReadStream('model_res.csv')
  .pipe(csv())
  .on('data', (data) => model[data.Image] = data.Results);

app.get('/', (req, res) => {
    res.send('Web-tier server is running!')
})

app.post('/', (req, res) => {
    const fname = req.files['inputFile'].name.split('.').slice(0, -1).join('.');
    res.send(`${fname}:${model[fname]}`)
})

app.listen(port, () => {
    console.log(`Web tier listening on port ${port}`)
})