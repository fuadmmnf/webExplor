const fs = require('fs')
const fse = require('fs-extra');

const args = require('minimist')(process.argv.slice(2))
const pti = require('puppeteer-to-istanbul');


// const merge = intervals => {
//     if (intervals.length < 2) return intervals;
//
//     intervals.sort((a, b) => a['start'] - b['start']);
//
//     const result = [];
//     let previous = intervals[0];
//
//     for (let i = 1; i < intervals.length; i += 1) {
//         if (previous['end'] >= intervals[i]['start']) {
//             previous = [previous['start'], Math.max(previous['end'], intervals[i]['end'])];
//         } else {
//             result.push(previous);
//             previous = intervals[i];
//         }
//     }
//
//     result.push(previous);
//
//     return result;
// };


const generateCoverage = (filename, content) => {
    let [coverage_content, scripts] = content.split('Scripts Mapping:\n')
    let scripts_mapping = JSON.parse(scripts.split('\n')[0])

    let cov_lines = coverage_content.replace(/text":\s*[^"0-9.]*([0-9.]+)/g, 'text":"$1"').split('\n')
    let coverages = []
    for (let i = 0; i < cov_lines.length - 1; i += 2) {
        if (cov_lines[i + 1] === '[]' || cov_lines[i + 1].length === 0) {
            continue
        }
        let cov = JSON.parse(cov_lines[i + 1])

        cov = cov.map(c => {
            c['text'] = scripts_mapping[c['text']]
            return c
        })

        coverages.push({
            time: cov_lines[i],
            cov_data: cov
        })
    }
    // console.log(coverages[0])
    // const accumulated_covs = [];
    let counter = 1
    let curr_minute = coverages[0].time.slice(14, 16)
    for (let i=0; i< coverages.length;  i++) {
        let cov_min = coverages[i].time.slice(14, 16)
        if (cov_min !== curr_minute) {
            // calculate using istanbul
            //copy file contents
            const srcDir = './res/my_approach/' + filename.split('_')[0] + '/' + counter + '/.nyc_output'
            const destDir = './res/my_approach/' + filename.split('_')[0] + '/' + (counter+1) + '/.nyc_output'

            fse.copySync(srcDir, destDir, function (err) {
                if (err) {
                    console.error(err);
                }
            })
            counter++
            curr_minute = cov_min
        }
            // accumulated_covs.push(...cov['cov_data'])
        pti.write(coverages[i]['cov_data'], {
            includeHostname: true,
            // storagePath: './res/webExplor/' + filename.split('_')[0] + '/.'+filename + counter
            storagePath: './res/my_approach/' + filename.split('_')[0] + '/' + counter + '/.nyc_output'
        })
    }

}

function readFiles(dirname, onFileContent) {
    filenames = fs.readdirSync(dirname)
    for (const filename of filenames) {
        let content = fs.readFileSync(dirname + filename, 'utf-8')
        onFileContent(filename, content)
    }
}

// readFiles('res/webExplor/logs', generateCoverage)
readFiles('./res/my_approach/logs/', generateCoverage)
// var file_content = fs.readFileSync(args.file, 'utf8')

