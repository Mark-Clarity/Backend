# MarkClarity Backend Scraper
# Developed by Marcos Meyer Hollerweger
# https://github.com/marcosh72
# For MarkClarity Team - Startup Weekend Women Denver - Feb 2018

from flask import Flask, Response, request
from flask_restful import reqparse
from flask_cors import CORS

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import json
import urllib
import requests

app = Flask(__name__)
CORS(app)
request_parser = reqparse.RequestParser()
request_parser.add_argument('query', type=str)
request_parser.add_argument('state', type=str)

def search_google(searchQuery):

	apiURL = 'https://www.googleapis.com/customsearch/v1?'
	key = '' # insert google search token
	searchID = '' # insert google search id

	reqURL = apiURL + "key=" + key + "&cx=" + searchID + "&q=" + searchQuery;

	try:
		r = requests.get(reqURL)
	except Exception as e:
		return {"data": {}, "error": repr(e)}

	try:
		retObj = r.json()
	except Exception as e:
		return {"data": {}, "error": repr(e)}
	else:
		return retObj

def search_uspto(searchQuery):
	apiUsername = "" # insert markerapi user here
	apiPassword = "" # insert markerapi pass here
	apiURL = 'https://www.markerapi.com/api/v1/trademark/search/'
	reqURL = apiURL + searchQuery + "/username/" + apiUsername + "/password/" + apiPassword

	try:
		r = requests.get(reqURL)
	except Exception as e:
		return {"data": {}, "error": repr(e)}

	try:
		retObj = r.json()
	except Exception as e:
		return {"data": {}, "error": repr(e)}
	else:
		return retObj

def search_de(searchQuery, driver):

	retObj = {'data': {}, 'error': ""}
	error = False

	try:
		driver.get("https://icis.corp.delaware.gov/ecorp/entitysearch/NameSearch.aspx")

		search_input = driver.find_element_by_css_selector('input[name="ctl00$ContentPlaceHolder1$frmEntityName"]')
		search_submit = driver.find_element_by_css_selector('input[type="submit"]')
		search_input.send_keys(searchQuery)
		search_submit.click()

	except Exception as e:
		retObj['error'] = "Error submitting search"
		error = True

	if not error:
		try:
			pageMessages = driver.find_element_by_css_selector("#ctl00_ContentPlaceHolder1_divCountsMsg")
			errorMessage =  pageMessages.get_property('innerText')

			if errorMessage:
				retObj['error'] = errorMessage
				error = True

		except NoSuchElementException as e:
			pass

	if not error:

		data = []

		tableRows = driver.find_elements_by_css_selector('#tblResults tr')
		for index, row in enumerate(tableRows):
			if index is 0:
				continue

			tableCols = row.find_elements_by_css_selector('td');
			thisRow = {
				"documentNumber": urllib.quote(tableCols[0].get_property('innerText').strip().encode('utf-8')),
				"name": urllib.quote(tableCols[1].get_property('innerText').strip().encode('utf-8')),
				"detailsUrl": urllib.quote(tableCols[1].find_element_by_tag_name('a').get_attribute('href').encode('utf-8'))
			}
			data.append(thisRow)

		retObj['data'] = data

	return retObj

def search_co(searchQuery, driver):

	retObj = {'data': {}, 'error': ""}
	error = False

	try:
		driver.get("http://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do")

		search_input = driver.find_element_by_css_selector('input[name="searchName"]')
		search_submit = driver.find_element_by_css_selector('input[type="submit"]')
		search_input.send_keys(searchQuery)
		search_submit.click()

	except Exception as e:
		retObj['error'] = "Error submitting search"
		error = True

	if not error:
		try:
			pageMessages = driver.find_element_by_css_selector("#pageMessages")
			messages = pageMessages.find_elements_by_css_selector('li')
			errorMessage = ""
			if len(messages):
				for message in messages:
					errorMessage += message.get_property('innerText').strip().encode('utf-8')
				retObj['error'] = errorMessage
				error = True
		except NoSuchElementException as e:
			pass

	if not error:

		data = []

		tableRows = driver.find_elements_by_css_selector('tr.odd')
		for row in tableRows:
			tableCols = row.find_elements_by_css_selector('td');
			thisRow = {
				"id": urllib.quote(tableCols[1].get_property('innerText').strip().encode('utf-8')),
				"documentNumber": urllib.quote(tableCols[2].get_property('innerText').strip().encode('utf-8')),
				"name": urllib.quote(tableCols[3].get_property('innerText').strip().encode('utf-8')),
				"event": urllib.quote(tableCols[4].get_property('innerText').strip().encode('utf-8')),
				"status": urllib.quote(tableCols[5].get_property('innerText').strip().encode('utf-8')),
				"form": urllib.quote(tableCols[6].get_property('innerText').strip().encode('utf-8')),
				"formationDate": urllib.quote(tableCols[7].get_property('innerText').strip().encode('utf-8')),
				"detailsUrl": urllib.quote(tableCols[1].find_element_by_tag_name('a').get_attribute('href').encode('utf-8'))
			}
			data.append(thisRow)

		retObj['data'] = data

	return retObj

def find_homonyms(searchQuery):

	apiURL = 'https://api.datamuse.com/words?sl='

	reqURL = apiURL + searchQuery;

	try:
		r = requests.get(reqURL)
	except Exception as e:
		return {"data": {}, "error": repr(e)}

	try:
		retObj = r.json()
	except Exception as e:
		return {"data": {}, "error": repr(e)}
	else:
		retObj = [a for a in retObj if a['score'] > 90]
		# retObj = [a for index, a in enumerate(retObj) if index < 3]
		print "length " + str(len(retObj))
		return retObj

@app.route('/homonyms', methods=['GET'])
def aksjbda():
	args = request_parser.parse_args()

	retObj = {'data': {}, 'error': ""}

	searchQuery = args['query']

	if not searchQuery :
		retObj['error'] = "Not enough input data"
	else:
		retObj = find_homonyms(searchQuery)

	return Response(response=json.dumps(retObj),
					status=200,
					mimetype="application/json")

@app.route('/state_search', methods=['GET'])
def state_search():
	args = request_parser.parse_args()

	retObj = {'data': {}, 'error': ""}

	searchQuery = args['query']
	searchState = args['state']

	if (not searchQuery) or (not searchState) :
		retObj['error'] = "Not enough input data"
	else:
		driver = start_browser()
		if driver:
			if searchState == "co":
				retObj = search_co(searchQuery, driver)
			elif searchState == "de":
				retObj = search_de(searchQuery, driver)
			else:
				retObj['error'] = "Not enough input data"
			
			try:
				driver.quit()
				driver.close()
			except Exception as e:
				pass
		else:
			retObj['error'] = "Server error"

	return Response(response=json.dumps(retObj),
					status=200,
					mimetype="application/json")

@app.route('/federal_search', methods=['GET'])
def federal_search():
	args = request_parser.parse_args()

	retObj = {'data': {}, 'error': ""}

	searchQuery = args['query']

	if not searchQuery :
		retObj['error'] = "Not enough input data"
	else:
		retObj = search_uspto(searchQuery)

	return Response(response=json.dumps(retObj),
					status=200,
					mimetype="application/json")	

@app.route('/google_search', methods=['GET'])
def google_search():
	args = request_parser.parse_args()

	retObj = {'data': {}, 'error': ""}

	searchQuery = args['query']

	if not searchQuery :
		retObj['error'] = "Not enough input data"
	else:
		retObj = search_google(searchQuery)

	return Response(response=json.dumps(retObj),
					status=200,
					mimetype="application/json")

def start_browser():
	try:
		chrome_options = Options()
		prefs = {"profile.default_content_setting_values.notifications" : 2}
		chrome_options.add_experimental_option("prefs",prefs)
		chrome_options.add_argument('--headless')
		chrome_options.add_argument('--disable-gpu')
		chrome_options.add_argument('--num-raster-threads=3')
		chrome_options.add_argument('--window-size=1440,900')
		chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36')

		driver = webdriver.Chrome(chrome_options=chrome_options)
	except Exception as e:
		return None

	return driver

if __name__ == "__main__":
	app.run(threaded=True, host='0.0.0.0')

# driver.close()
# driver.quit()