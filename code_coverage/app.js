const fs = require('fs')
const pti = require('puppeteer-to-istanbul')
const args = require('minimist')(process.argv.slice(2))

var coverage_content = fs.readFileSync(args.file, 'utf8')
var coverages = coverage_content.split('\n').filter(function (element, index, array) {
    return (index % 2 === 1) && element.length > 0
}).map(function (element) {
    return JSON.parse(element)
});

pti.write([...coverages[coverages.length-1]], { includeHostname: true , storagePath: './res/webExplor/.nyc_output' })

