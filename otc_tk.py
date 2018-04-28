# otc_tk.py
# Ex0's OTC Toolkit Python Module for XChat
# ======================================================================
#  
#  Copyright 2013 Exodeus <exodeus@digitalfrost.net>
#  Version 0.3.0 completed 05.28.2013
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
# ======================================================================


import xchat
import gnupg
import pycurl
import cStringIO

# Define our module.
__module_name__ = "Ex0's OTC Toolkit"
__module_version__ = "0.3.0"
__module_author__ = "Exodeus"
__module_description__ = "This is a handy Toolkit for #bitcoin-otc on freenode. Built for the XChat2 IRC Client"

xchat.prnt("\002\00302%s:\00302 \00304[[[LOADED]]]\00304\002" % (__module_name__))

# Create some menus on the menubar
xchat.command('MENU -p5 ADD "OTC Toolkit"')
xchat.command('MENU ADD "OTC Toolkit/GPG EAuth" "OTCTK EAUTH"')
xchat.command('MENU ADD "OTC Toolkit/-"')
xchat.command('MENU ADD "OTC Toolkit/Get Voice" "MSG gribble voiceme"')

# Create some menus for our nicklist popup
xchat.command('MENU ADD "$NICK/OTC Toolkit"')
xchat.command('MENU ADD "$NICK/OTC Toolkit/Get WoT Rating" "MSG gribble getrating %s"')
xchat.command('MENU ADD "$NICK/OTC Toolkit/GPG Information" "MSG gribble gpg info %s"')


# Print Version Information
def otcauth_ver():
	xchat.prnt("\002\00302%s\00302\002 Version: \002\00303%s\00303\002 By: \002\00304%s\00304\002" % (__module_name__, __module_version__, __module_author__))
	xchat.prnt(__module_description__)
	
	return xchat.EAT_NONE

# Print out the Help info
def otcauth_help(topic):
	if len(topic) < 2:
		switch = "basic"
	else:
		switch = topic[1].lower()
		etc = "".join(topic[1])

	if switch == "basic":
		xchat.prnt("""\002/OTCTK  
=======================================\002
An OTC authentication script for XChat2
	OPTIONS:
		\002\00302HELP\00302\002
				Display help page
				or use help <topic>
				for more help about
				<topic>	

		\002\00302EAUTH\00302\002
				Used to start the
				GPG Auth process.

		\002\00302VERSION\00302\002
				Returns the scripts
				version string.""")

	elif switch == "eauth":
		xchat.prnt("\002\00304/OTCTK\00304 \00302eauth\00302\002 \n\tAuth Help")
	elif switch == "version":
		xchat.prnt("\002\00304/OTCTK\00304 \00302version\00302\002 \n\tPrints out the current version of the tool")
	else:
		xchat.prnt("I don't know anything about topic: %s" % (str(etc)))
	
	return xchat.EAT_XCHAT

# GPG Decryption Function.
# Use GPG to decrypt the string gribble gave us and send back the verify string
def otcauth_gpg_decrypt(encrypted_string):
	gpg = gnupg.GPG(use_agent=True)
	gpg.encoding = 'utf-8'
	auth_string = gpg.decrypt(encrypted_string)

	return auth_string

# Get our string to decrypt from gribble
global eauthCheck
eauthCheck = False
def otcauth_gpg_auth(word, word_eol, userdata):
	global eauthCheck
	if word[0] == ':gribble!~gribble@unaffiliated/nanotube/bot/gribble' and eauthCheck == True:
		# Get our url
		url = str(word[-1])
		buf = cStringIO.StringIO()
		# Check to make sure we got the proper link.
		if url[:-16] == "http://bitcoin-otc.com/otps/":
			# Link Good! cURL our string and decrypt.
			curl = pycurl.Curl()
			curl.setopt(curl.URL, url)
			curl.setopt(curl.USERAGENT, """Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)""")
			curl.setopt(curl.WRITEFUNCTION, buf.write)
			curl.perform()

			# Decrypt and message gribble back the verify string.
			auth_string = buf.getvalue()
			buf.close()
			xchat.command("MSG gribble everify %s" % otcauth_gpg_decrypt(auth_string))
			eauthCheck = False
			
	return xchat.EAT_NONE
# Hook the server event when gribble messages us.
xchat.hook_server("PRIVMSG", otcauth_gpg_auth)

	
# The callback function to our hook that ties it all together	
def otcauth_cb(word, word_eol, userdata):
	if len(word) < 2:
		switch = "help"
	else:
		switch = str(word[1]).lower()
	
	if switch == "help":
		otcauth_help(word[1:])
	elif switch == "version":
		otcauth_ver()
	elif switch == "eauth":
		nick = xchat.get_info('nick')
		xchat.command("MSG gribble eauth %s" % (nick))
		global eauthCheck
		eauthCheck = True
	elif switch == "bauth":
		xchat.prnt("RESERVED FOR FUTURE FUNCTIONALITY")
	else:
		xchat.prnt("\002\00304Invalid Option:\00304\002 %s not defined" % (word[1]))
	
	return xchat.EAT_XCHAT
	
# Hook our functions to the callback handler
xchat.hook_command("OTCTK", otcauth_cb, help="'/OTCTK help' for more help")

# An unload callback function to clean up 
def otcauth_unload_cb(userdata):
	# Remove our MENU's 
	xchat.command('MENU DEL "OTC Toolkit/GPG EAuth" "otctk eauth"')
	xchat.command('MENU DEL "OTC Toolkit/-"')
	xchat.command('MENU DEL "OTC Toolkit/Get Voice"')
	xchat.command('MENU DEL "OTC Toolkit"')

	# Remove nicklist popup menus
	xchat.command('MENU DEL "$NICK/OTC Toolkit/Get WoT Rating"')
	xchat.command('MENU DEL "$NICK/OTC Toolkit/GPG Information"')
	xchat.command('MENU DEL "$NICK/OTC Toolkit"')
	
	# Print out our unloaded message.
	xchat.prnt("\002\00302%s:\00302 \00304[[[UNLOADED]]]\00304\002" % __module_name__)
	return xchat.EAT_XCHAT
	
# And hook into our unload event
xchat.hook_unload(otcauth_unload_cb)
