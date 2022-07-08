Skyhawk Flight Instruments jQuery Plugin
===================

The Skyhawk Flight Instrument plugin is a fork of the excellent jQuery Flight Indicators Plugin (https://github.com/sebmatton/jQuery-Flight-Indicators), with several additions and updated graphics. The instruments are modelled after those typically found in a Cessna 172 Skyhawk aircraft.

This plugin allows you to display high quality flight indicators using HTML, CSS3, jQuery and SVG images. The methods make customization and real time implementation really easy. Further, since all the images are vector svg you can resize the indicators to your application without any quality loss!

Currently supported indicators are :

* Air Speed
* Attitude
* Altimeter
* Turn Coordinator
* Heading
* Vertical Speed

Examples
-------------------
Here is an example of a full dashboard:

![demo_example](https://raw.githubusercontent.com/uw-ray/Skyhawk-Flight-Instruments/master/docs/dashboard.png "Indicator examples")

The image below shows a zoomed altimeter. Vector images allows you to keep high quality render with large indicators.

![demo_highres](https://raw.githubusercontent.com/uw-ray/Skyhawk-Flight-Instruments/master/docs/zoom_example.png "High resolution indicator")

Usage
-------------------
### Initialization

To use this plugin you need to import a few files in the head of your HTML file :

```html
<script src="js/jquery-1.11.3.js"></script>
<script src="js/d3.min.js"></script>
<script src="js/jquery.flightindicators.js"></script>
<link rel="stylesheet" type="text/css" href="css/flightindicators.css" />
```

### Using the plugin
Create a `<span>` section to put an indicator in :

```html
<span id="attitude"></span>
```

Then, when the span is ready in the DOM (maybe you need to wait for document ready), you can run the indicator function :

```js
var indicator = $.flightIndicator('#attitude', type, options);
```
Where the first argument is the selector, the type value specify the indicator type and the options overwrite the default settings.

To display the most simple indicator, as for example the attitude indicator, we use :

```js
var indicator = $.flightIndicator('#attitude', 'attitude');
```

The type may be `airspeed`, `attitude`, `altimeter`, `turncoordinator`, `heading` or `variometer`. If the type is not correct, nothing will display.

Initial settings can be modified using the `options` parameter. Here are the valid options and the default settings :

```js
var options = {
	size : 200,				// Sets the size in pixels of the indicator (square)
	showBox : true,			// Sets the visibility of the box behind the instruments
	showScrews: true,		// Sets the visibility of the four screws around the instruments
	airspeed: 0,			// Air speed in knots for an air speed indicator
	roll : 0,				// Roll angle in degrees for an attitude indicator
	pitch : 0,				// Pitch angle in degrees for an attitude indicator
	off_flag: false			// Off flag for an attitude indicator
	altitude: 0,			// Altitude in feets for an altimeter indicator
	pressure: 30,			// Pressure in inHg for an altimeter indicator
	turn: 0,				// Turn direction for turn coordinator
	slip: 0,				// Slip ball position for turn coordinator (0 to 1; 0.5 is middle)
	heading: 0,				// Heading angle in degrees for an heading indicator
	beaconone: 0, 			// Angle of first beacon on the heading indicator
	beacononeshow: true,	// Sets the visibility of the first beacon on the heading indicator
	beacontwo: 0, 			// Angle of second beacon on heading indicator
	beacontwoshow: true,	// Sets the visibility of the second beacon on the heading indicator
	vario: 0,				// Variometer in 1000 feets/min for the variometer indicator
	img_directory : 'img/'	// The directory where the images are saved to
}
```

The options parameters are optionnals.

### Updating the indicator informations
Some methods are used to update the indicators, giving the opportunity to create realtime GUI !

The way to use it is really simple.

```js
var attitude = $.flightIndicator('#attitude', 'attitude');
attitude.setRoll(30); // Sets the roll to 30 degrees
```

Here are the valid methods :

```js
indicator.setAirSpeed(speed);				// Set speed of an airspeed indicator
indicator.setRoll(roll);					// Set roll of an attitude indicator
indicator.setPitch(pitch);					// Set pitch of an attitude indicator
indicator.setOffFlag(visible);				// Set visibility of Off flag of an attitude indicator
indicator.setAltitude(altitude);			// Set altitude of an altimeter indicator
indicator.setPressure(pressure, milibars);	// Set pressure of an altimeter indicator (inHg by default). If the second parameter is true, the units will be set to milibars.
indicator.setTurn(turn);					// Set angle of turn of a turn coordinator
indicator.setSlip(slip);					// Set position of slip ball of a turn coordinator. Range is between 0 and 1, 0.5 being the middle.
indicator.setHeading(heading);				// Set heading of a heading indicator
indicator.setBeaconOne(heading, visibile)	// Set angle of the first beacon of a heading indicator and its visibility
indicator.setBeaconTwo(heading, visibile)	// Set angle of the second beacon of a heading indicator and its visibility
indicator.setVario(vario);					// Set climb speed of a variometer indicator
indicator.resize(size);						// Set size in pixels of the indicator
indicator.toggleBox();						// Toggle background box of the indicator
indicator.toggleScrews();					// Toggle background screws of the indicator
```

Notes
-----------

#### Turn Coordinator:

In order to allow the slip ball to move smoothly, a path animation was required. Loading of this path is done via D3.js, however this will cause issues in Google Chrome when running a turn coordinator directly from an HTML file (ie file:// path). 

To circumvent this issue (for development purposes mainly), the main JS file will inject an SVG path into the DOM. If you modify **turn_ball_path.svg** make sure to also update the highlighted line below, with your new path:

![demo_highres](https://raw.githubusercontent.com/uw-ray/Skyhawk-Flight-Instruments/master/docs/move_path.png "move_path woes")

Authors and License
-----------
Authors : Raymond Blaga (raymond.blaga@gmail.com), Edward Hanna (edward.hanna@senecacollege.ca), Pavlo Kuzhel (pavlo.kuzhel@senecacollege.ca), Sébastien Matton (seb_matton@hotmail.com)

Skyhawk Flight Instruments was made for use in an online course with the purpose of training future pilots, developed by Seneca College Centre for Development of Open Technology.

The project is published under GPLv3 License. See LICENSE file for more informations

Thanks
---------
Thanks to Sébastien Matton and everyone involved in the making of the jQuery Flight Indicators Plugin.
