const minZoom = 0;
const maxZoom = 19;
const map = L.map('map', {
    minZoom: minZoom,
    maxZoom: maxZoom
});
map.attributionControl.addAttribution(
    '<a href="https://github.com/jaluebbe/GPSTracker">Source on GitHub</a>');
// add link to an imprint and a privacy statement if the file is available.
function addPrivacyStatement() {
    var xhr = new XMLHttpRequest();
    xhr.open('HEAD', "/static/datenschutz.html");
    xhr.onload = function() {
        if (xhr.status === 200)
            map.attributionControl.addAttribution(
                '<a href="/static/datenschutz.html" target="_blank">Impressum & Datenschutzerkl&auml;rung</a>'
            );
    }
    xhr.send();
}
addPrivacyStatement();

function addOSMVectorLayer(styleName, region, layerLabel) {
    let myLayer = L.maplibreGL({
        style: '../api/vector/style/' + region + '/' + styleName + '.json',
        attribution: '&copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
    layerControl.addBaseLayer(myLayer, layerLabel);
    // make sure to reprint the vector map after being selected.
    map.on('baselayerchange', function(eo) {
        if (eo.name === layerLabel) {
            myLayer._update();
        }
    });
    return myLayer;
};

L.control.scale({
    'imperial': false
}).addTo(map);
var layerControl = L.control.layers({}, {}, {
    collapsed: true,
    position: 'topright'
}).addTo(map);

fetch('/api/vector/regions')
    .then(response => response.json())
    .then(data => {
        if (data.length > 0) {
            const mapRegion = data[0];
            addOSMVectorLayer("osm_basic", mapRegion, "OSM Basic").addTo(map);
            addOSMVectorLayer("osm_bright", mapRegion, "OSM Bright");
            addOSMVectorLayer("osm_liberty", mapRegion, "OSM Liberty");
            addOSMVectorLayer("osm_positron", mapRegion, "OSM Positron");
            map.setView([52.2775, 8.0415], 12);
        } else {
            console.warn('No regions available.');
        }
    })
    .catch(error => {
        console.error('Error fetching regions:', error);
    });
