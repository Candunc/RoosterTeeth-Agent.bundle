import re
import os

API_BASE_URL = 'https://svod-be.roosterteeth.com'

def APIRequest(url):
	request = JSON.ObjectFromURL(url)

#	if 'error' in request.data:
#		Log('RoosterTeethAgent - Error in API Request '{}' - {}'.format(url, request.data['error']))
#		return None

	matches = len(request['data'])
	Log('Found {} matches'.format(matches))

	if matches != 0:
		return request['data']
	else:
		return None

def GetMediaDir(media, file=False):
	for s in media.seasons if media else []: # TV_Show:
		for e in media.seasons[s].episodes:
			return media.seasons[s].episodes[e].items[0].parts[0].file if file else os.path.dirname(media.seasons[s].episodes[e].items[0].parts[0].file)

def ActualUpdateEpisode(episode, episode_number, filename, show_slug):
	episode_name = os.path.splitext(os.path.basename(filename))[0].split('-',1)[1]
	Log('UpdateEpisode() - {}'.format(episode_name))

	url = '{}/api/v1/search/episodes?query={}&page=1&per_page=100'.format(API_BASE_URL, String.Quote(episode_name, usePlus=False))

	for match in APIRequest(url):
		if match['attributes']['show_slug'] == show_slug:
			request = match
			break

	publish_date = request['attributes']['sponsor_golive_at'].split('T',1)[0]

	episode.title = request['attributes']['display_title']
	episode.summary = request['attributes']['description']
	episode.originally_available_at = Datetime.ParseDate(publish_date).date()
	episode.duration = request['attributes']['length']*1000

	poster = None

	for photo in request['included']['images']:
		if photo['type'] == 'episode_image':
			poster = photo['attributes']['large']
			break

	Log(dir(episode))
	if poster != None and poster not in episode.thumbs:
		episode.thumbs[poster] = Proxy.Media(HTTP.Request(poster).content, sort_order=1)


def Search(results, media, lang, manual):
	Log(''.ljust(157, '-'))
	Log('search() - Title: "%s"  -> "%s"' % (media.title, media.episode))

	results.Append(MetadataSearchResult(
		id=str(media.title),
		name=media.title,
		year=None,
		lang=lang,
		score=100
	))

def Update(metadata, media, lang, force):
	Log(''.ljust(157, '='))
	Log('update() - metadata.id: "%s", metadata.title: "%s"' % (metadata.id, metadata.title))
	
	directory = GetMediaDir(media)
	folders = directory.split(os.path.sep)
	show_slug = folders[-2]

	show_url = '{}/api/v1/shows/{}'.format(API_BASE_URL, show_slug)
	show_request = APIRequest(show_url)[0]
	publish_date = show_request['attributes']['published_at'].split('T',1)[0]

	metadata.title		= show_request['attributes']['title']
	metadata.summary	= show_request['attributes']['summary']
	metadata.studio		= 'RoosterTeeth'
	metadata.originally_available_at = Datetime.ParseDate(publish_date).date()

	poster, banner, background, fallback = None, None, None, None

	for photo in show_request['included']['images']:
		if photo['attributes']['image_type'] == 'poster':
			poster = photo['attributes']['large']

		if photo['attributes']['image_type'] == 'hero':
			background = photo['attributes']['large']

		if photo['attributes']['image_type'] == 'logo':
			banner = photo['attributes']['large']

		if photo['attributes']['image_type'] == 'mobile_hero':
			fallback = photo['attributes']['large']

	if poster == None:
		poster = fallback

	if background != None and background not in metadata.art:
		metadata.art[background] = Proxy.Media(HTTP.Request(background).content, sort_order=1)

	if banner != None and banner not in metadata.banners:
		metadata.banners[banner] = Proxy.Media(HTTP.Request(banner).content, sort_order=1)

	if poster != None and poster not in metadata.posters:
		metadata.posters[poster] = Proxy.Media(HTTP.Request(poster).content, sort_order=1)

	Log('update() ended')
	@parallelize
	def UpdateEpisodes():
		for year in media.seasons:
			for episode_number in media.seasons[year].episodes:
				episode = metadata.seasons[year].episodes[episode_number]
				filename = media.seasons[year].episodes[episode_number].items[0].parts[0].file
				@task  # Create a task for updating this episode
				def UpdateEpisode(episode=episode, episode_number=episode_number, filename=filename, show_slug=show_slug): 
					ActualUpdateEpisode(episode, episode_number, filename, show_slug)

def Start():
	HTTP.CacheTime             = CACHE_1DAY
	#HTTP.Headers['User-Agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)'

class RoosterTeethAgent(Agent.TV_Shows):
	name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = ('RoosterTeeth', True, False, None, [Locale.Language.English,], ['com.plexapp.agents.localmedia'] )  #, 'com.plexapp.agents.opensubtitles'
	
	def search(self, results, media, lang, manual): Search(results, media, lang, manual)
	def update(self, metadata, media, lang, force): Update(metadata, media, lang, force)
