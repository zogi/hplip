<!--
/*
 (c) Copyright 2001-2007 Hewlett-Packard Development Company, L.P.

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

 Author: Pete Parks

*/
-->


var hilite_button = "../images/button1d.png";
var default_button = "../images/button1.png";
var newWindow;
var location_ref;
var alt_location_ref  = "#";
var button_time = 400;
var elem;
var main_window;

function setMainWindow(win) {
    main_window = win;
}

function setLocationRef(ref) {
    alt_location_ref = ref;
}

function getLocationRef() {
    return alt_location_ref;
}

function setButtonHiliteTime(time) {
    button_time = time;
}

function setButtonImages(default_image, hilite_image) {
    default_button = default_image;
    hilite_button = hilite_image;
}


function changeRadio(el) {
    el.checked = el.checked ? false : true;
    return true;
};

function getContentText(divText, divID) {
    if(divText.length < 500) {
        document.getElementById(divID).innerHTML = '<a>' + divText + '</a>';
    } else {
        var elem = document.getElementById(divID).innerHTML='<div id="notesScrollBox"></table><tr><td align="center" valign="center" bgcolor="#ffffff"><textarea cols="62" rows="12" wrap="on" id="scrollTextArea" onkeyup="sTextArea.innerText=scrollTextArea.innerText">'+ divText +'</textarea></td></tr><tr bgcolor"#dddddd"><td align="center" bgcolor="#ffffff"><br/></div>';  
    }
};

function getContentLine(len, divText, divID) {
    if(len < 8) {
        document.getElementById(divID).innerHTML = '<a>' + divText + '</a>';
    } else {
        var searchTerm = /<br\/>/g;
        divText = divText.replace(searchTerm, "\n");
        var elem = document.getElementById(divID).innerHTML='<div id="notesScrollBox"></table><tr><td align="center" valign="center" bgcolor="#FFFFFF"><textarea cols="62" rows="12" wrap="on" id="scrollTextArea" onkeyup="sTextArea.innerText=scrollTextArea.innerText">'+ divText +'</textarea></td></tr><tr bgcolor"#dddddd"><td align="center" bgcolor="#ffffff"><br/></div>';  
    }
};

function generateHeader() {
    document.getElementById("header_box").innerHTML='<div class="header_title_class"><div id="hp_blue_logo"><img src="images/hplogo.png" alt=""/></div><div id="header_title">HP Linux Imaging and Printing (HPLIP)</div><div id="header_title2">HP Linux Imaging and Printing (HPLIP)</div><div id="header_subtitle">Installer</div><div id="header_subtitle2">Installer</div><div id="tux_logo"><img src="images/tux.png" alt=""/></div></div>';
};

function resetButton(button_name) {
    elem.src = default_button;
    window.location.href = location_ref;
    setLocationRef("#");
}

function hiliteButton(button_name) {
    setTimeout('resetButton();', button_time); 
    elem = document.getElementById(button_name).childNodes[1]; 
    elem.src = hilite_button;
}


function indexClickActions(button_name, default_path) {
    //alert("location_ref - Url Path: " + default_path);
    if(default_path == "????") {
        alert("An unimplement path has occured!");
        location_ref = "test";
    } 
    
    location_ref = default_path;
    if(getLocationRef() != "#") {
        location_ref = getLocationRef();
    }
    //alert("location_ref - Url Path: " + location_ref);
    hiliteButton(button_name);
}

function getStoppedStatus(filename) {
    var localPath = GetLocalDataFile(filename);
    //alert("Get Status - Url Path: " + localPath);
    var http = new XmlLoader(localPath);
    var serverResponse = http.submitLoaderRequest("POST", false);
    statusValue = parseInt(serverResponse);
    return statusValue;
}

function setStoppedStatus(filename) {
    var localPath = GetLocalDataFile(filename);
    //alert("Stop Status - Url Path: " + localPath);
    var http = new XmlLoader(localPath);
    http.submitLoaderRequest("POST", false);
}

function todoOnQuit(path) {
    window.location.href = path;
    window.opener.location.href = path;
    indexClickActions( "quit_button", path);
    window.close();
    fixMainWindow();
    setStoppedStatus("signal_stop");
}


function fixMainWindow() {
    var width = 660;
    var height = 500;
    var x = 0.5 * (window.opener.screen.width - width);
    var y = 0.5 * (window.opener.screen.height - height);
    window.opener.resizeTo(width + 2, height + 100);
    window.opener.moveTo(x,y);
    window.opener.reload(true);
}

function openNewWindow(state) { 
    var width = 660;
    var height = 500;
    new_window = null; 
    var x = 0.5 * (window.screen.width - width);
    var y = 0.5 * (window.screen.height - height);
    window.toolbar.visible = false;
    window.menubar.visible = false;
    if(state != 0) {
        new_window = window.open("http://localhost:8080/welcome","","dependent=0, resizable=0, status=0, toolbar=0, scrollbars=0" + ',width=' + width + ',height=' + height + ',left=' + x + ', top=' + y);
    }

    if(new_window != null) { 
        window.resizeTo(width - 100, height - 100);
        window.moveTo(x + 100, y + 100);
    }
    return new_window;
}


function GetLocalDataFile(filename)
{
    var localPath = GetAbsoluteFilePath(filename);
    return localPath;
}


function GetAbsoluteFilePath(filename)
{
    var pgURL = document.URL;
    var n = pgURL.lastIndexOf("\/");
    path = pgURL.substring(n+1);
    var newpath = pgURL.replace(path, "");
    newpath = newpath + filename
    return newpath;
}


function isMozilla(){
    
    return (document.implementation && document.implementation.createDocument) ? 1 : 0;
}

function isKonquerorBase() {
    return (BrowserDetect.browser == 'Konqueror') ? 1 : 0;
}

function isFireFoxBase() {
    return (BrowserDetect.browser == 'Firefox') ? 1 : 0;
}

function isSafariBase() {
    return (BrowserDetect.browser == 'Safari') ? 1 : 0;
}

function isGaleonBased() {
    return (BrowserDetect.browser == 'Galeon') ? 1 : 0;
}

/*
Credit: The Joe Clark Micropatronage Project

Site: http://www.quirksmode.org/js/detect.html
        
Code:  Browser detect

*/
var BrowserDetect = {
	init: function () {
		this.browser = this.searchString(this.dataBrowser) || "An unknown browser";
		this.version = this.searchVersion(navigator.userAgent)
			|| this.searchVersion(navigator.appVersion)
			|| "an unknown version";
		this.OS = this.searchString(this.dataOS) || "an unknown OS";
	},
	searchString: function (data) {
		for (var i=0;i<data.length;i++)	{
			var dataString = data[i].string;
			var dataProp = data[i].prop;
			this.versionSearchString = data[i].versionSearch || data[i].identity;
			if (dataString) {
				if (dataString.indexOf(data[i].subString) != -1)
					return data[i].identity;
			}
			else if (dataProp)
				return data[i].identity;
		}
	},
	searchVersion: function (dataString) {
		var index = dataString.indexOf(this.versionSearchString);
		if (index == -1) return;
		return parseFloat(dataString.substring(index+this.versionSearchString.length+1));
	},
	dataBrowser: [
		{ 	string: navigator.userAgent,
			subString: "OmniWeb",
			versionSearch: "OmniWeb/",
			identity: "OmniWeb"
		},
		{
			string: navigator.vendor,
			subString: "Apple",
			identity: "Safari"
		},
		{
			prop: window.opera,
			identity: "Opera"
		},
		{
			string: navigator.vendor,
			subString: "iCab",
			identity: "iCab"
		},
		{
			string: navigator.vendor,
			subString: "KDE",
			identity: "Konqueror"
		},
		{
			string: navigator.userAgent,
			subString: "Firefox",
			identity: "Firefox"
		},
		{
			string: navigator.vendor,
			subString: "Camino",
			identity: "Camino"
		},
		{		// for newer Netscapes (6+)
			string: navigator.userAgent,
			subString: "Netscape",
			identity: "Netscape"
		},
		{
			string: navigator.userAgent,
			subString: "MSIE",
			identity: "Explorer",
			versionSearch: "MSIE"
		},
		{
			string: navigator.userAgent,
			subString: "Gecko",
			identity: "Mozilla",
			versionSearch: "rv"
		},
		{ 		// for older Netscapes (4-)
			string: navigator.userAgent,
			subString: "Mozilla",
			identity: "Netscape",
			versionSearch: "Mozilla"
		}
	],
	dataOS : [
		{
			string: navigator.platform,
			subString: "Win",
			identity: "Windows"
		},
		{
			string: navigator.platform,
			subString: "Mac",
			identity: "Mac"
		},
		{
			string: navigator.platform,
			subString: "Linux",
			identity: "Linux"
		}
	]

};
BrowserDetect.init();


/*
Credit: Mar 12, 2005 by lobo235

Site: http://www.netlobo.com/div_hiding.html
        
Code:  Showing and Hiding a DIV using CSS and Javascript

*/
function toggleLayer(whichLayer)
{
    if (document.getElementById) {
        // this is the way the standards work
        var style2 = document.getElementById(whichLayer).style;
        style2.display = style2.display? "":"block";
    } else if (document.all) {
        // this is the way old msie versions work
        var style2 = document.all[whichLayer].style;
        style2.display = style2.display? "":"block";
    } else if (document.layers) {
        // this is the way nn4 works
        var style2 = document.layers[whichLayer].style;
        style2.display = style2.display? "":"block";
    }
}


/*
Credit: No Name Listed

Site: http://www.jools.net/projects/ruby/crypto/
        
Code:  String Encoding (encode64)

*/
var keyStr = "ABCDEFGHIJKLMNOP" +
   			"QRSTUVWXYZabcdef" +
   			"ghijklmnopqrstuv" +
   			"wxyz0123456789+/" +
   			"=";

   function encode64(input) {
     var output = "";
     var chr1, chr2, chr3 = "";
     var enc1, enc2, enc3, enc4 = "";
     var i = 0;

     do {
   	 chr1 = input.charCodeAt(i++);
   	 chr2 = input.charCodeAt(i++);
   	 chr3 = input.charCodeAt(i++);

   	 enc1 = chr1 >> 2;
   	 enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
   	 enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
   	 enc4 = chr3 & 63;

   	 if (isNaN(chr2)) {
   		enc3 = enc4 = 64;
   	 } else if (isNaN(chr3)) {
   		enc4 = 64;
   	 }

   	 output = output + 
   		keyStr.charAt(enc1) + 
   		keyStr.charAt(enc2) + 
   		keyStr.charAt(enc3) + 
   		keyStr.charAt(enc4);
   	 chr1 = chr2 = chr3 = "";
   	 enc1 = enc2 = enc3 = enc4 = "";
     } while (i < input.length);

     return output;
   }
