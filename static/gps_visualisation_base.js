var map = L.map('map', {
    minZoom: 7,
    maxZoom: 19
});
map.setView([49.0, 9.0], 7);
map.attributionControl.addAttribution(
    '<a href="https://github.com/jaluebbe/GPSTracker">Source on GitHub</a>');
// add link to privacy statement
//map.attributionControl.addAttribution(
//    '<a href="static/datenschutz.html" target="_blank">Datenschutzerkl&auml;rung</a>');
var topPlusOpenLayer = L.tileLayer.wms('https://sgx.geodatenzentrum.de/wms_topplus_open', {
    layers: 'web',
    format: 'image/png',
    transparent: true,
    minZoom: 1,
    maxNativeZoom: 18,
    maxZoom: 19,
    attribution: '&copy <a href="https://www.bkg.bund.de">BKG</a> 2019, ' +
        '<a href= "http://sg.geodatenzentrum.de/web_public/Datenquellen_TopPlus_Open.pdf" >data sources</a> '
});
var otmLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    maxZoom: 15,
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
        'contributors, SRTM | Map style: &copy; ' +
        '<a href="https://opentopomap.org">OpenTopoMap</a> ' +
        '(<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
});
esriImagery = L.layerGroup([
    L.esri.basemapLayer('Imagery', {
        maxZoom: 18
    }),
    L.esri.basemapLayer('ImageryLabels', {
        maxZoom: 18
    })
]);
var SwissFederalGeoportal_NationalMapColor = L.tileLayer('https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg', {
    attribution: '&copy; <a href="https://www.swisstopo.admin.ch/">swisstopo</a>',
    minZoom: 7,
    maxZoom: 19,
    bounds: [[45.398181, 5.140242], [48.230651, 11.47757]]
});
var SwissFederalGeoportal_SWISSIMAGE = L.tileLayer('https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg', {
    attribution: '&copy; <a href="https://www.swisstopo.admin.ch/">swisstopo</a>',
    minZoom: 7,
    maxZoom: 19,
    bounds: [[45.398181, 5.140242], [48.230651, 11.47757]]
});
var openSeaMap = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
    attribution: 'Map data: &copy; <a href="http://www.openseamap.org">OpenSeaMap</a> contributors'
});
var openPtMap = L.tileLayer('http://openptmap.org/tiles/{z}/{x}/{y}.png', {
    minZoom: 4,
    maxZoom: 17,
    attribution: 'Map data: &copy; <a href="http://www.openptmap.org">OpenPtMap</a> contributors'
});
var openRailwayMap = L.tileLayer('https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png', {
    minZoom: 2,
    maxZoom: 17,
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Map style: &copy; <a href="https://www.OpenRailwayMap.org">OpenRailwayMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
});
L.control.scale({
    'imperial': false
}).addTo(map);
baseLayers = {
    "TopPlusOpen": topPlusOpenLayer,
    "OpenTopoMap": otmLayer,
    "Esri Imagery": esriImagery,
    "swiss map": SwissFederalGeoportal_NationalMapColor,
    "SWISSIMAGE": SwissFederalGeoportal_SWISSIMAGE
};
otherLayers = {
    "OpenSeaMap": openSeaMap,
    "Openptmap": openPtMap,
    "OpenRailwayMap": openRailwayMap
};
var layerControl = L.control.layers(baseLayers, otherLayers, {
    collapsed: L.Browser.mobile, // hide on mobile devices
    position: 'topright'
}).addTo(map);
topPlusOpenLayer.addTo(map);
