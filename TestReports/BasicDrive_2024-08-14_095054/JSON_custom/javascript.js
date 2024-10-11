﻿(function($) {
	$.fn.hasScrollBar = function() {
		return this.get(0).scrollHeight > this.height();
	}
})(jQuery);

var $window = $(window),
	$document = $(document);

function initSubReport(reportConfig) {
	// jQuery Version
	$('#jqversion').text( $('#jqversion').text().replace('$jqversion',$.fn.jquery) );

	// Haeufig verwendete JQuery Selektoren cachen und ggf. default Werte/Verhalten definieren
	var $contentWrapper=$('#contentWrapper'),
		$infoFrame=reportConfig.enableInfoFrame === true ? $('#infoFrame') : $('#infoFrame').hide(),
		$infoHandler=reportConfig.enableInfoFrame === true ? $('#infoHandler') : $('#infoHandler').hide(),
		$tableHead=$('#tableHead'),
		$list=$('#list'),
		$traceanalysis=$('#traceanalysis'),
		$analysisjobs=$('#analysisjobs'),
		$recordings=$('#recordings'),
		$mapping=$('#mapping'),
		$report=$('#report'),
		$scrollbar=$('#scrollbar'),
		$lightbox=$('#lightbox').hide(),
		$imgbox=$('#imgbox'),
		$hiddenlayer=$('#hiddenlayer').click(function(event) {
			if (event.target != event.delegateTarget) {
				return false;
			}
			$imgbox.empty();
			$hiddenlayer.hide();
			return true;
		}),
		$closebox=$('#closebox').click(function() {
			$hiddenlayer.trigger('click');
		}),
		$navigation=$('#navigation'),
		$previous=$('#previous'),
		$previousPage=$('#previousPage'),
		$multiplier=$('#multiplier'),
		$next=$('#next'),
		$nextPage=$('#nextPage'),
		$tooltipSettings=reportConfig.enableTooltip === true ? $('#tooltipSettings').addClass('on').text(lang.toggleSettings.on) : $('#tooltipSettings').addClass('off').text(lang.toggleSettings.off),
		$infoFrameSettings=reportConfig.enableInfoFrame === true ? $('#infoFrameSettings').addClass('on').text(lang.toggleSettings.on) : $('#infoFrameSettings').addClass('off').text(lang.toggleSettings.off);

	var reportHeaderCellWidth = [10,5,25,20,20,10,10], // Breite der jeweiligen Zellen in Pixel festlegen
		reportSpanWidths = [];

	// alle moeglichen Eintraege der Navigation
	var tabArr = {
			a_details: ['details',lang.navigation.details],
			a_config: ['config',lang.navigation.config],
			a_mapping: ['mapping',lang.navigation.mapping],
			a_report: ['report',lang.navigation.report],
			a_recordings: ['recordings',lang.navigation.recordings],
			a_traceanalysis: ['traceanalysis',lang.navigation.traceanalysis],
			a_analysisjobs: ['analysisjobs',lang.navigation.analysisjobs]
		},
		showResultAboveNav = [];

	// Zufaelligen String in globaler Variable speichern. Wird verwendet um die Tooltips der dynamisch erzeugten Tabellen beim Scrollen zu entfernen. 
	window.globalVars = {
		blockTimeout: rndString(8)
	};

	// <--- variablen einrichten | Json laden und anzeigen --->

	var lineHeight = 25, // Eine Zeile wird so viele Pixel hoch, inkl. 1 Pixel Border jeweils
		linesPerPage = calcLinesPerPage(), // Wie viele Elemente koennen pro Seite angezeigt werden? Schaetzen anhand der Zeilenhoehe (lineHeight) ...
		pageStart = 0,			// Start- und Endwerte fuer das Blaettern
		pageEnd = linesPerPage, // (Initialwerte)
		mouseOnScrollbar = false, // Befindet sich die Maus ueber der kuenstlichen Scrollbar?
		enableScroll = true, // true, wenn mehr DB Eintraege als darstellbare Zeilen vorhanden sind, sonst false
		reportFocus = false, // Aktuelle hervorgehobene Zeile im Testcase
		initScript = false,
		indentWidth = 10, // so viele Pixel pro Einrueckung
		scrollbarThreshold = 500; // bei mehr Linien wird das Schiebeelement der Scrollbar minimal angezeigt

	// Script initialisieren
	if(!initScript) {
		initScript=true;
		var execInit = function() {
			if(HasTraceAnalyses) {
				showResultAboveNav[showResultAboveNav.length] = {
					'id': 'trace_pos',
					'storeArray': TraceCount,
					'insertAfter': $('#a_traceanalysis'),
					'jQ_cache': false,
					'position': 0,
					'onclickcb': function(target_id) {
						var $target = $('#trace_id_'+target_id);
						if ($target.length==0) return false;
						window.location.hash = '#trace_id_'+target_id;
						/*var new_position = $target.offset();
						$contentWrapper.scrollTop(new_position.top);*/
						$target.trigger('click');
						return false;
					}
				};
			} else if (HasAnalysisJobs) {
				showResultAboveNav[showResultAboveNav.length] = {
					'id': 'trace_pos',
					'storeArray': JobCount,
					'insertAfter': $('#a_analysisjobs'),
					'jQ_cache': false,
					'position': 0,
					'onclickcb': function(target_id) {
						var $target = $('#trace_id_'+target_id);
						if ($target.length==0) return false;
						window.location.hash = '#trace_id_'+target_id;
						/*var new_position = $target.offset();
						$contentWrapper.scrollTop(new_position.top);*/
						$target.trigger('click');
						return false;
					}
				}
			}

			for(var i=0; i<showResultAboveNav.length;i++) {
				if(showResultAboveNav[i]['jQ_cache'] === false) {
					if(showResultAboveNav[i]['storeArray']['error'].length>0) {
						showResultAboveNav[i]['jQ_cache'] = $('<div class="count_container" style="background-color: rgb(180, 0, 0);"><span id="'+showResultAboveNav[i]['id']+'"></span>'+showResultAboveNav[i]['storeArray']['error'].length+'</div>').data('type','error').insertAfter(showResultAboveNav[i]['insertAfter']);
					} else if(showResultAboveNav[i]['storeArray']['failed'].length>0) {
						showResultAboveNav[i]['jQ_cache'] = $('<div class="count_container" style="background-color: rgb(242, 87, 87);"><span id="'+showResultAboveNav[i]['id']+'"></span>'+showResultAboveNav[i]['storeArray']['failed'].length+'</div>').data('type','failed').insertAfter(showResultAboveNav[i]['insertAfter']);
					}
				}

				if(showResultAboveNav[i]['jQ_cache'] != false) {
					showResultAboveNav[i]['jQ_cache'].css('cursor','pointer').on('click',{'i': i},function(event) {
						var self = $(this),
							type = self.data('type'),
							i = event.data.i,
							pos = showResultAboveNav[i]['position']; // aktuelle Fehler Position cachen

						showResultAboveNav[i]['insertAfter'].trigger('click'); // Click auf Navigation routen

						// click callback ggf. ausfuehren
						if( ( showResultAboveNav[i]['id']=='report_pos'&&pageEOL>linesPerPage)||(showResultAboveNav[i]['id']=='trace_pos'&&$contentWrapper.hasScrollBar())) {
							showResultAboveNav[i]['onclickcb'](showResultAboveNav[i]['storeArray'][type][pos]);
							$('#'+showResultAboveNav[i]['id']).text((pos+1)+'/'); // Fehlerposition anzeigen, bspw.: 3/14
						}
						
						// internen Positionszeiger weiterschieben und ggf. auf Null setzen falls Ende erreicht ist
						showResultAboveNav[i]['position']+=1;
						if(showResultAboveNav[i]['position']==showResultAboveNav[i]['storeArray'][type].length) {
							showResultAboveNav[i]['position']=0;
						}
					});
				}
			}

			$hiddenlayer.css('display','none');

			// Tooltips fuer statische Elemente generieren:
			// *Traceanalyse oder AnalysisJobs
			// *Aufnahmen
			// *Mapping
			window.generateStaticTooltips = [
				{
					'jq_selector': $('#traceList'),
					'jq_target': $traceanalysis
				},{
					'jq_selector': $('#traceList'),
					'jq_target': $analysisjobs
				},{
					'jq_selector': $('#recList'),
					'jq_target': $recordings
				},{
					'jq_selector': $('#mapList'),
					'jq_target': $mapping
				}
			];

			for (var i = 0; i < window.generateStaticTooltips.length; i++) {
				$('li:not(.darkgrey)',window.generateStaticTooltips[i]['jq_selector']).each(function() {
					var self = $(this),
						hiddenData = self.find('.hiddenData');

					if(hiddenData.length>0) {
						self.data('i',i)
							.Focus()
							.Tooltip({
								id: self.attr('id'),
								title: '<a class="goto" style="display: none;">'+lang.tooltip.jumpToEntry_static+'</a><span>'+lang.tooltip.titleText+'</span>',
								titleDblClick: lang.tooltip.titleDblClick,
								body: hiddenData.html(),
								target: window.generateStaticTooltips[i]['jq_target'],
								indentPos: 1,
								lineHeight: lineHeight,
								staticIncrementor: i,
								gotoCallback: function(j) {
									var id_str = '#'+self.attr('id'),
										$this = $(this);

									var parentHeight = $contentWrapper.height(),
										parentOffset = $contentWrapper.offset().top,
										liHeight = $this.height(),
										liTop = $this.offset().top;

									if (liTop-parentOffset < 0 || liTop-parentOffset+liHeight > parentHeight) {
										// ... nicht vollstaendig sichtbar, also hinspringen
										window.location.hash = id_str;
									}

									/*var new_position = self.offset();
									$contentWrapper.scrollTop(new_position.top);*/

									$(id_str).trigger('click'); // Focus triggern
									return false;
								},
								infoFrame: $infoFrame
							});
					}
				});
			};
			$window.trigger('resize');
			initNavigation();
		};

		if(HasTestCase) {
			asyncLoadScript(jsonFile, function() {
			//$.getScript(jsonFile, function() { // alternativ kann hier auch mit jQuery geladen werden, das funktioniert jedoch nicht in Chrome fuer lokale Dateien:
				showResultAboveNav[showResultAboveNav.length] = {
					'id': 'report_pos',
					'storeArray': ReportCount,
					'insertAfter': $('#a_report'),
					'jQ_cache': false,
					'position': 0,
					'onclickcb': function(target_id) {
						pageStart = target_id-1;
						pageEnd = pageStart+linesPerPage;
						checkPageDelimiter();

						showLineContent(pageStart,pageEnd);
						moveScrollbar();
						$('#report_id_'+(target_id-1)).trigger('click');
					}
				};
				execInit();
			});
		} else {
			execInit();
		}
	}

	function initNavigation() {

		if ($('#a_report').length == 1 && $('#report').length == 1) {
			$('#a_report').addClass('select');
			$('#report').css('display','block');
		} else {
			$('#a_details').addClass('select');
			$('#details').css('display','block');
		}

		if ( window.self !== window.top ) {
			// detect anchors -> testcase, trace - analysis - jobs, mapping, recordings

			var href = window.location.href;
			if(href.indexOf('?report') > -1) {
				$('#a_report').trigger('click');
			} else if (href.indexOf('?trace') > -1) {
				$('#a_traceanalysis, #a_analysisjobs').trigger('click');
				if(href.indexOf('&id=') > 1) {
					// id aus string lösen und zu id scrollen & anklicken
					var id = href.split('?trace&id=')[1] || 0;
					var id_string = 'trace_id_'+id;
					window.location.hash = '#'+id_string;
					$('#'+id_string).trigger('click');
				}
			} else if (href.indexOf('?recordings') > -1) {
				$('#a_recordings').trigger('click');
			} else if (href.indexOf('?mapping') > -1) {
				$('#a_mapping').trigger('click');
			}
		}
	};

	// Prozent umrechnen in Pixel - fuer Tabellenkopf
	function proz2pixl(input, max) {
		return input/100*max;
	};

	// Erzeugt einen x-stelligen Zufallsstring
	function rndString(len) {
		var l = parseInt(len, 10);
		return Math.random().toString(36).substring(l>0?len-1:7); // return rnd string of custom length or default
	};

	function asyncLoadScript(url, callback) { // JSON Datei einlesen
		var script=document.createElement('script'),
			firstScript=document.getElementsByTagName('script')[0];
		
		script.async=true;
		script.src=url;
		if(typeof callback==='function') { // Callback an das Event script.onload anhaengen
			script.onload=function() {
				callback();
				script.onload=undefined; // .onload event leeren nach Aufruf, damit es nicht mehrfach ausgeloest wird
			};
			script.onreadystatechange=function() {
				if(script.readyState==='loaded' || script.readyState==='complete') {
					script.onload(); // onload event ausfuehren nach erfolgreicher Statusaenderung
				}
			};
		}
		if(!firstScript.parentNode.insertBefore(script, firstScript)) {
			return false;
		}
	};

	function showLineContent(start,end) { // Zeilen von start bis end darstellen
		window.globalVars.blockTimeout=rndString(8);

		$('div[id^="tt_"]:not(.keep)', $report).remove(); // Tooltips loeschen, die nicht angeheftet sind
		$list.empty(); // Anzeige leeren

		for(var i=pageStart; i<(pageStart+linesPerPage); i++) {
			var j=i-pageStart,
				line=getJsonLine(i),
				idStyle='',
				imgSrc='',
				htmlCode='<li id="report_id_'+i+'">';
			
			if(!line) { // Falls fuer eine erwartet Zeilennummer kein DB Eintrag vorhanden ist, wird eine leere Zeile angezeigt
				htmlCode+='<span style="border-top: 0;"></span></li>';
				$list.append(htmlCode);
				continue;
			}

			if(line['id']['tdStyle']!='') {
				for(var iter in line['id']['tdStyle']) {
					idStyle+=' '+iter+': '+line['id']['tdStyle'][iter]+';';
				}
			}

			var idHtml = line['id']['extern'];
			if(line['notes']['noteImg'] != '') {
				idHtml+='<div style="text-indent: 0; position: absolute; right: 0; top: 0; height: 25px; width: 25px; background-color: '+line['notes']['orgResultColor']+';"><img src="'+line['notes']['noteImg']+'" alt="" style="position: relative; top: 4px; right: 0; margin: 0 4px;"></div>';
				htmlCode+='<span class="centered" style="width: '+(reportSpanWidths[0]-25)+'px; position: relative; padding-right: 25px;'+idStyle+'">'+idHtml+'</span>';
			} else {
				htmlCode+='<span class="centered" style="width: '+reportSpanWidths[0]+'px; position: relative;'+idStyle+'">'+idHtml+'</span>';
			}

			htmlCode+='<span class="centered" style="width: '+reportSpanWidths[1]+'px;">'+line['time']['txt']+'</span>';

			if(line['action']['execLevel']>0) {
				htmlCode+='<span style="width: '+(line['action']['execLevel']*indentWidth)+'px;"></span>';
			}

			imgSrc=line['action']['img-link'].length > 1 ? '<img src="'+line['action']['img-link']+'" alt="Teststep-Icon">' : '';

			htmlCode+='<span style="width: '+(reportSpanWidths[2]-indentWidth*line['action']['execLevel'])+'px; background-color: '+line['bgcolor']+'; font-weight: '+line['action']['style']+';">'+imgSrc+line['action']['txt']+'</span>';

			if(typeof line['package-name'] != 'undefined') {
				htmlCode+='<span style="width: '+reportSpanWidths[3]+'px; background-color: '+line['bgcolor']+'; font-weight: '+line['name']['style']+';"><a href="'+line['package-name']+'" class="subPackageLink">'+line['name']['txt']+'</a></span>';
			} else {
				htmlCode+='<span style="width: '+reportSpanWidths[3]+'px; background-color: '+line['bgcolor']+'; font-weight: '+line['name']['style']+';">'+line['name']['txt']+'</span>';
			}
			
			htmlCode+='<span style="width: '+reportSpanWidths[4]+'px; background-color: '+line['bgcolor']+'; font-weight: '+line['info']['style']+';">'+line['info']['txt']+'</span>';
			htmlCode+='<span style="width: '+reportSpanWidths[5]+'px; background-color: '+line['bgcolor']+'; font-weight: '+line['targetvalue']['style']+';">'+line['targetvalue']['txt']+'</span>';
			htmlCode+='<span style="width: '+reportSpanWidths[6]+'px; background-color: '+line['bgcolor']+'; background: linear-gradient(to right,'+line['bgcolor']+' 0%, #E5E5E5 100%);">'+line['comment']['txt']+'</span></li>';

			$list.append(htmlCode);

			var $lastLi=$('li:last',$list).Focus();

			if ($('#tt_'+i).length==0) { // pruefen ob schon ein tooltip offen ist, falls nicht ein entsprechendes objekt erzeugen
				$lastLi.Tooltip({
					id: i,
					title: '<a class="goto" style="display: none;" title="'+lang.tooltip.jumpToEntry_dynamic+'">'+lang.tooltip.testcase+': '+line['id']['extern']+'</a><span>'+lang.tooltip.titleText+'</span>',
					titleDblClick: lang.tooltip.titleDblClick,
					body: function() {
						var ttHtml ='<div class="tableContainer"><table rules="all"><tr>'; // tooltip output buffer

						ttHtml+='<td style="'+idStyle+'">'+line['id']['extern']+'</td>';
						ttHtml+= line['notes']['noteImg'] != '' ? '<td style="background-color: '+line['notes']['orgResultColor']+';"><img src="'+line['notes']['noteImg']+'"></td>' : '';
						ttHtml+='<td style="">'+line['time']['txt']+'</td>';
						ttHtml+='<td style="background-color: '+line['bgcolor']+'; font-weight: '+line['action']['style']+';">'+imgSrc+line['action']['txt']+'</td>';
						ttHtml+='<td style="background-color: '+line['bgcolor']+'; font-weight: '+line['name']['style']+';">'+line['name']['txt']+'</td>';
						ttHtml+='<td style="background-color: '+line['bgcolor']+'; font-weight: '+line['info']['style']+';">'+line['info']['txt']+'</td>';
						ttHtml+='<td style="background-color: '+line['bgcolor']+'; font-weight: '+line['targetvalue']['style']+';">'+line['targetvalue']['txt']+'</td>';
						ttHtml+='<td style="background-color: '+line['bgcolor']+'; background: linear-gradient(to right,'+line['bgcolor']+' 0%, #E5E5E5 100%);">'+line['comment']['txt']+'</td>';
						ttHtml+='</tr></table></div>',
						repLength=line['repEntities'].length, // anzahl report entities
						comLength=line['repComments'].length; // anzahl user comments

						if(repLength>0) { // ReportEntities: imageentity, textentity, tableentity_cell
							for(var j=0;j<repLength;j++) {
								const reportEntity = line['repEntities'][j];
								const entityType = reportEntity['type'];
								if(entityType == 'imageentity') {
									url = reportEntity['data'][1]
									ttHtml+='<div class="tableContainer"><table><tr><th><b>' + reportEntity['data'][0] + '</b></th></tr><tr><td>';
									if (url) {
										ttHtml+='<div class="smallPicture"><img src="' + reportEntity['data'][1] + '"><a href="' + reportEntity['data'][1] + '" target="_blank" class="newTab">+</a></div>';
									} else {
										ttHtml+='<div class="imageNotFound" style>Image of original report was not found.</div>';
									}
									ttHtml+='</td></tr></table></div>';
								} else if (entityType == 'image_expectation_entity') {
									const header1 = reportEntity['data'][0];
									const header2 = reportEntity['data'][1];
									const expectedImage = reportEntity['data'][2];
									const actualImage = reportEntity['data'][3];
									
									ttHtml+='<div class="tableContainer"><table>';

									ttHtml+='<tr>';
									for (header of [header1, header2]) {
										ttHtml+='<th><b>' + header + '</b></th>';
									}
									ttHtml+='</tr>';
									
									ttHtml+='<tr>'
									for (image of [expectedImage, actualImage]) {
										ttHtml+='<td>';
										if (image) {
											ttHtml+='<div class="smallPicture"><img src="' + image + '"><a href="' + image + '" target="_blank" class="newTab">+</a></div>';
										} else {
											ttHtml+='<div class="imageNotFound" style>Image of original report was not found.</div>';
										}
										ttHtml+='</td>';
									}
									ttHtml+='</tr>'
									ttHtml+='</table></div>';}
								else if(entityType == 'textentity') {
									ttHtml+='<div class="tableContainer"><table rules="all"><tr><td>'+reportEntity['data']+'</td></tr></table></div>';} 
								else if(entityType == 'tableentity_cell') {
									ttHtml+='<div class="tableContainer"><table rules="all"><tr><td>'+reportEntity['data'][0].join('</td><td>')+'</td></tr>';
									for(var k=1; k<reportEntity['data'].length; k++) {
										ttHtml+='<tr><td>'+reportEntity['data'][k].join('</td><td>')+'</td></tr>';
									}
									ttHtml+='</table></div>';
								}
							}
						}
						if(comLength>0) { // UserComments
							ttHtml+='<div class="tableContainer"><table rules="all"><tr class="darkgrey"><th>'+lang.tooltip.comments.author+'</th><th>'+lang.tooltip.comments.date+'</th><th>'+lang.tooltip.comments.comment+'</th><th>'+lang.tooltip.comments.subsequentRating+'</th></tr>';
							for (var j=0;j<comLength;j++) {
								ttHtml+='<tr><td>'+line['repComments'][j]['author']+'</td>';
								ttHtml+='<td>'+line['repComments'][j]['date']+'</td>';
								ttHtml+='<td>'+line['repComments'][j]['text']+'</td>';
								ttHtml+='<td>'+line['repComments'][j]['overriddenResult']+'</td></tr>';
							};
							ttHtml+='</table></div>';
						}
						if(typeof line['duration'] == 'object') { // Execution duration
							ttHtml+='<div class="tableContainer"><table rules="all">';
							for(var key in line['duration']) {
								ttHtml+='<tr><td>'+key+'</td><td>'+line['duration'][key]+'</td></tr>';
							}
							ttHtml+='</table></div>';
						}
						if(typeof line['repScm'] == 'object') { // SCM Informations
							ttHtml+='<div class="tableContainer"><table rules="all">';
							for(var key in line['repScm']) {
								ttHtml+='<tr><td>'+key+'</td><td>'+line['repScm'][key]+'</td></tr>';
							}
							ttHtml+='</table></div>';
						}
						return ttHtml;
					}(line),
					target: $report,
					lineHeight: lineHeight,
					blockTimeout: window.globalVars.blockTimeout,
					gotoCallback: function(id) {
						if(HasTestCase && enableScroll === true) {
							if ($('#report_id_'+id).length==0) {
								pageStart=id;
								pageEnd=pageStart+linesPerPage;

								checkPageDelimiter();

								showLineContent(pageStart, pageEnd);
								moveScrollbar();
							}
							$('#report_id_'+id).trigger('click');
						}
					},
					infoFrame: $infoFrame
				});
			} // if tooltip schon offen
		} // for
		checkButtons();
		return false;
	};

	function getJsonLine(line) { // einzelnen Eintrag aus Json holen unter Angabe der globalen ID
		var t_line = separateNumber(line),
			jsData = mainfunc('jsObj'+t_line[0]);
		
		if(typeof(jsData[t_line[1]])!='undefined') {
			return jsData[t_line[1]];
		}
	};

	function separateNumber(input) { // Zahl (mittels Modulo) anhand der stepSize in 2 Zahlen zerlegen, die der Struktur des Json entsprechen
		return [Math.round(input/stepSize-0.5),input%stepSize];
	};

	function calcLinesPerPage() { // Berechnen wie viele Linien dargestellt werden koennen
		return Math.round( ($contentWrapper.height() - $tableHead.height() ) / lineHeight - 2.5 );
	};

	function calcScrollheight() { // Berechnen des Schwellenwertes, ab dem der Scrollschieber minimal dargestellt wird
		return (pageEOL+3)*lineHeight;
	};

	function mainfunc(func) { // dynamisch erzeugten Funktionsnamen ausfuehren
		if (typeof window[func] === 'function') {
			return this[func]();
		}
	};

	function checkButtons() { // Buttons (de-)aktivieren bei Erreichen von Anfang oder Ende
		if(pageStart!=0) {
			$previous.removeAttr('disabled');
			$previousPage.removeAttr('disabled');
		}
		if(pageEnd==pageEOL) {
			$next.attr('disabled','');
			$nextPage.attr('disabled','');
		}
		if(pageEnd!=pageEOL) {
			$next.removeAttr('disabled');
			$nextPage.removeAttr('disabled');
		}
		if(pageStart==0) {
			$previous.attr('disabled','');
			$previousPage.attr('disabled','');
		}
		return false;
	};

	// Multiplier zum Blaettern aus input Feld auslesen
	function getMultiplier() {
		var multiplier = parseInt($multiplier.val());
		if(typeof(multiplier)=='undefined' || multiplier=='' || multiplier < 1 || isNaN(multiplier)) {
			multiplier=1;
			$multiplier.val(1);
		}
		return multiplier;
	};

	$previous.add($next).add($previousPage).add($nextPage).click(function(event) { // Blaettern durch Inhalt mittels Knoepfen am unteren Bildrand
		event.preventDefault();

		if(HasTestCase && enableScroll === true) {
			var multiplier = getMultiplier();
			
			switch($(this).attr('id')) {
				case 'next':
					pageStart+=multiplier;
					pageEnd+=multiplier;
					if(pageEnd>=pageEOL) {
						pageEnd=pageEOL;
						pageStart=pageEnd-linesPerPage;
					}
					break;
				case 'previous':
					pageStart-=multiplier;
					pageEnd-=multiplier;
					if(pageStart<=0) {
						pageStart=0;
						pageEnd=pageStart+linesPerPage;
					}
					break;
				case 'nextPage':
					pageStart+=linesPerPage;
					pageEnd+=linesPerPage;
					if(pageEnd>=pageEOL) {
						pageEnd=pageEOL;
						pageStart=pageEnd-linesPerPage;
					}
					break;
				case 'previousPage':
					pageStart-=linesPerPage;
					pageEnd-=linesPerPage;
					if(pageStart<=0) {
						pageStart=0;
						pageEnd=pageStart+linesPerPage;
					}
					break;
				default:
			}

			showLineContent(pageStart, pageEnd);
			moveScrollbar();

		}
		return false;
	});

	// Scrollbarschieber entsprechend der dargestellten Zeilen positionieren
	function moveScrollbar() {
		if(HasTestCase && enableScroll === true) {
			var t_aufpunkt = pageStart,
				t_proz = t_aufpunkt/(pageEOL-linesPerPage)*100,
				t_scrollPos = t_proz/100*($scrollbar.prop('scrollHeight')-$scrollbar.prop('offsetHeight'));
			$scrollbar.scrollTop(t_scrollPos);
		}
		return false;
	};

	// mouseOnScrollbar auf true/false setzen wenn die Maus ueber der Scrollbar ist bzw. diese verlaesst
	$scrollbar.hover(function() {
		mouseOnScrollbar=true;
		return false;
	}, function() {
		mouseOnScrollbar=false;
		return false;
	});
	
	// Tasten events verarbeiten
	$document.on('keyup',function(event) {
		event.preventDefault();
		if(mouseOnScrollbar==false && HasTestCase && enableScroll === true) {
			var validKeyPress=true;
			switch(event.keyCode) {
				/*case 33: // Bild hoch
					scrollbar.scrollTop(scrollbar.scrollTop()-3000);
					break;
				case 34: // Bild runter
					scrollbar.scrollTop(scrollbar.scrollTop()+3000);
					break;*/
				case 35: // Ende
					$scrollbar.scrollTop(scrollbar.prop('scrollHeight')-scrollbar.prop('offsetHeight'));
					break;
				case 36: // Pos1
					$scrollbar.scrollTop(0);
					break;
				case 38: // Pfeiltaste hoch
					var t_multiplier = getMultiplier();
					$multiplier.val(1);
					$previous.trigger('click');
					$multiplier.val(t_multiplier);
					break;
				case 40: // Pfeiltaste runter
					var t_multiplier = getMultiplier();
					$multiplier.val(1);
					$next.trigger('click');
					$multiplier.val(t_multiplier);
					break;
				case 37: // Pfeiltaste links
					$previousPage.trigger('click');
					break;
				case 39: // Pfeiltaste rechts
					$nextPage.trigger('click');
					break;
				default:
					validKeyPress=false;
			}
			if(validKeyPress) {
				scrollContent();
			}
		}
		return false;
	});

	if(window.addEventListener) { // EventListener fuer Window-Mausrad-Scroll Events
		window.addEventListener('DOMMouseScroll', getMouseWheel, false); // Moz
	}
	window.onmousewheel = document.onmousewheel = getMouseWheel; // IE+Opera+chrome

	/*
	 *	Info zum Scrollen:
	 *	Die angezeigte Scrollbar wird in einem 10.000 Pixel hohen Div erzeugt (overflow: vertical-y)
	 *	Die angezeigten Inhalte sind folglich nicht direkt mit der Scrollbar verknuepft, dazu werden alle
	 *	Scroll Events ueber JS abgefangen und auf die Anzeige der Inhalte simuliert.
	 */
	function getMouseWheel(event) { // Mausrad scrollen verarbeiten
		if(mouseOnScrollbar==false && HasTestCase && enableScroll === true) {
			var retDelta = 0;
		
			if(!event) {
				event=window.event; // ie
			}
		
			if(event.wheelDelta) { // IE/chrome/(opera?)
				retDelta=event.wheelDelta/120;
			} else if(event.detail) { // moz
				retDelta=event.detail/-3;
			}
			
			$scrollbar.scrollTop($scrollbar.scrollTop()+(retDelta*-50)); // Scroll-Faktor: -50
			scrollContent(); // angezeigte Inhalte aktualisieren
		}
		return false;
	};

	function scrollContent() { // Inhalte nach Scrollen neu rendern
		if(HasTestCase && enableScroll === true) {
			var proz = $scrollbar.scrollTop()/($scrollbar.prop('scrollHeight')-$scrollbar.prop('offsetHeight'))*100; // Position des Scrollbalkens prozentual bestimmen und auf Inhalte umrechnen

			pageStart=Math.round(proz/100*(pageEOL-linesPerPage));
			pageEnd=pageStart+linesPerPage;
			
			checkPageDelimiter();

			showLineContent(pageStart,pageEnd);
		}
		return false;
	};

	$scrollbar.scroll(function(event) { // Scrollevent der Scrollbar filtern und nur zulassen, wenn der Cursor ueber Scrollbar ist
		if(mouseOnScrollbar==true) {
			scrollContent();
		}
		return false;
	});

	function checkPageDelimiter() { // Prueft Start- und Endpunkte, verhindert Uebertreten des gueltigen id Bereiches
		if(pageStart <= 0) {
			pageStart = 0;
			pageEnd = linesPerPage;
		}
		if(pageEnd >= pageEOL) {
			pageEnd = pageEOL;
			pageStart = pageEOL-linesPerPage;
		}
		return false;
	};

	// <--- Json laden und anzeigen | Navigation umschalten --->

	// Navigationsleiste: Farbe beim Mouseover wechseln und Klicks verarbeiten
	$('li > a',$navigation).hover(function() {
		var self = $(this);
		if(!self.hasClass('select')) {
			self.parent().css('background-color','rgb(237,139,0)'); // mouseover: neue Hintergrundfarbe anzeigen
		}
		return false;
	}, function() {
		var self = $(this);
		if(!self.hasClass('select')) {
			self.parent().css('background-color',''); // mouseout: Hintergrundfarbe wieder entfernen
		}
		return false;
	}).click(function(event) {
		var self = $(this);
		event.preventDefault();
		if(!self.hasClass('select')) {
			var a_id = $('li > a.select',$navigation).prop('id'); // aktuell ausgewaehlte id
			$('#'+tabArr[a_id][0]).css('display','none'); // Aktuell angezeigtes Element verstecken
			$('#'+tabArr[self.prop('id')][0]).css('display','block'); // selektierte id anzeigen

			if(self.prop('id') == 'a_report') { // overflow nur fuer Report deaktivieren
				$contentWrapper.css('overflow','hidden');
				$window.trigger('resize');
			} else {
				$contentWrapper.css('overflow','auto');
			}

			if(self.prop('id')=='a_report'||self.prop('id')=='a_recordings'||self.prop('id')=='a_traceanalysis'||self.prop('id')=='a_analysisjobs') {
				if(reportConfig.enableInfoFrame) {
					$infoFrame.add($infoHandler).show();
				} else {
					$infoFrame.add($infoHandler).hide();
				}
				$window.trigger('resize');
			} else {
				$infoFrame.add($infoHandler).hide();
				// todo: bedienelement blockieren
			}

			$('li > a.select',$navigation).removeClass('select');
			self.addClass('select').parent().css('background-color','');
		}
		return false;
	});

	// <--- Navigation | Resize --->

	var resizeTimeout=false;
	// Aenderung der Fenstergroeße erfassen und Interfaceparameter entsprechend anpassen
	$window.resize(function() {
		if(resizeTimeout === false) {
			resizeTimeout = setTimeout(function() {
				// Hoehe des $contentWrapper neu errechnen (in Pixel)
				var contentWrapperHeight = $window.height()-$('header').height()-$('footer').height()-2*parseInt($contentWrapper.css('margin-top'),10);
				if($infoFrame.is(':visible') && reportConfig.enableInfoFrame===true) {
					contentWrapperHeight-=$infoFrame.outerHeight();
				}
				$contentWrapper.height(contentWrapperHeight);

				// Breite der Liste an $contentWrapper anpassen
				$list.width($contentWrapper.width());
				$tableHead.width($contentWrapper.width());

				// Breite der Zellen im Testreport-Tabellenkopf errechnen (in Pixel)
				var thc = $('li', $tableHead).children();
				for(var i=0; i<reportHeaderCellWidth.length; i++) {
					reportSpanWidths[i] = proz2pixl(reportHeaderCellWidth[i], $tableHead.width());
					$(thc[i]).width(reportSpanWidths[i]);
				}
				// max einrueckung des testreports fixen
				indentWidth=10;
				if (reportSpanWidths[2] - maxExecLevel*indentWidth < 20) {
					indentWidth=5;
					if (reportSpanWidths[2] - maxExecLevel*indentWidth < 20) {
						indentWidth=1;
					}
				}

				// Zeilen pro Seite erneut errechnen
				linesPerPage = calcLinesPerPage();

				// Start- und Endpunkt ueberpruefen und ggf. korrigieren
				// Scrollbar ein- bzw. ausblenden
				if(HasTestCase === true) {
					if(pageEOL <= linesPerPage) {
						pageEnd=pageEOL;
						pageStart=0;
						enableScroll=false;
						$scrollbar.css('display','none');
					} else {
						enableScroll=true;
						if(pageEOL >= scrollbarThreshold) {
							$('div:first-child', $scrollbar).height(10000);
						} else {
							$('div:first-child', $scrollbar).height(calcScrollheight());
						}
						$scrollbar.css('display','block');
						pageEnd=pageStart+linesPerPage;
						checkPageDelimiter();
					}

					if(isNaN(pageStart) || isNaN(pageEnd)) {
						pageStart=0;
						pageEnd=linesPerPage;
					}
					showLineContent(pageStart,pageEnd); // Tabelle mit Inhalt fuellen
					moveScrollbar(); // Scrollbarposition aktualisieren
				}
				resizeTimeout=false;
			}, 100);
		}
		return false;
	});

	// <--- Resize | Patches: Info Popup (rechte, untere Ecke) --->

	var $patches = $('#patches').data('presence','hide'),
		$closePatches = $('#closePatches').data('presence','hide').css('display','none');
	$('#version').hover(function() {
		if($patches.data('presence') == 'hide') $patches.data('presence','show').css('display','block');
	}, function() {
		if($patches.data('presence') == 'show') $patches.data('presence','hide').css('display','none');
	}).click(function() {
		if($patches.data('presence') == 'show') {
			$closePatches.data('presence','show').fadeIn('slow');
			$patches.data('presence','keep').css('display','block');
		}
	});

	$closePatches.click(function() {
		$closePatches.data('presence','hide').css('display','none');
		$patches.data('presence','hide').css('display','none');
	});

	// <--- Patches Info Popup | InfoFrame Drag Handler --->

	var startHeight = $infoFrame.height(),
		startBottom = parseInt($infoHandler.css('bottom'), 10),
		handlerHeight = $infoHandler.height();

	$infoHandler.on('mousedown mouseup dblclick', function(event) {
		event.preventDefault();
		if (event.type == 'mousedown') {
			var mousedownCoord = event.pageY;
			$document.on('mousemove', function(event2) {
				var delta = mousedownCoord-event2.pageY;
				
				var newBottomPos = delta+parseInt($infoHandler.css('bottom'), 10);
				if(event2.pageY <= $window.height()-35 && event2.pageY >= $('header').height()+10) {
					$infoHandler.css('bottom', newBottomPos);
					$infoFrame.height($infoFrame.height()+delta);
					$window.trigger('resize');
					mousedownCoord = event2.pageY;
				}
			});
		} else if (event.type == 'mouseup') {
			$document.off('mousemove');
		} else if (event.type == 'dblclick') {
			$infoHandler.css('bottom',startBottom);
			$infoFrame.height(startHeight);
			$window.trigger('resize');
		}
	});


	// Tooltip & Infoframe Settings
	// Info frame de-/aktivieren
	$infoFrameSettings.click(function () {
		if (reportConfig.enableInfoFrame) {
			$infoFrameSettings.removeClass('on').addClass('off').text(lang.toggleSettings.off);
			reportConfig.setEnableInfoFrame(false)
			$infoFrame.add($infoHandler).hide();
		} else {
			$infoFrameSettings.removeClass('off').addClass('on').text(lang.toggleSettings.on);
			reportConfig.setEnableInfoFrame(true)
			$infoFrame.add($infoHandler).show();
		}
		$window.trigger('resize');
	});

	// Tooltips de-/aktivieren
	$tooltipSettings.click(function () {
		if (reportConfig.enableTooltip) {
			$tooltipSettings.removeClass('on').addClass('off').text(lang.toggleSettings.off);
			reportConfig.setEnableTooltip(false)
			$('.ttWindow').remove();
		} else {
			$tooltipSettings.removeClass('off').addClass('on').text(lang.toggleSettings.on);
			reportConfig.setEnableTooltip(true)
		}
		$window.trigger('resize');
	});
};