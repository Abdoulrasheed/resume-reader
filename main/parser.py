#!/usr/bin/env python
import csv
from pprint import pprint
from django.conf import settings
from .utils import convertDocxToText, convertPDFToText
import nltk, os, subprocess, code, glob, re, traceback, sys


try:
    nltk.download('punkt')
    nltk.download('words')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')
except:
    pass
    
class Parse():
    # List (of dictionaries) that will store all of the values
    # For processing purposes
    lines = []
    tokens = []
    information=[]
    sentences = []
    inputString = ''
    

    def __init__(self, f, verbose=False):
        # info is a dictionary that stores all the data obtained from parsing
        info = {}
        
        self.inputString, info['extension'] = self.readFile(f)         
        info['fileName'] = f

        self.tokenize(self.inputString)
        

        self.getEmail(self.inputString, info)

        self.getPhone(self.inputString, info)

        self.getName(self.inputString, info)

        self.Qualification(self.inputString, info)

        self.getExperience(self.inputString, info, debug=verbose)
        
        self.information.append(info)
        self.result = info


    def readFile(self, fileName):
        '''
        Read a file given its name as a string.
        Modules required: os
        UNIX packages required: antiword, ps2ascii
        '''
        extension = fileName.split(".")[-1]
        if extension == "txt":
            f = open(fileName, 'r')
            string = f.read()
            f.close() 
            return string, extension
        elif extension == "doc":
            # Run a shell command and store the output as a string
            # Antiword is used for extracting data out of Word docs. Does not work with docx, pdf etc.
            return subprocess.Popen(['antiword', fileName], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0], extension
        elif extension == "docx":
            try:
                return convertDocxToText(fileName), extension
            except:
                return ''
        #elif extension == "rtf":
        #    try:
        #        return convertRtfToText(fileName), extension
        #    except:
        #        return ''
        #        pass
        elif extension == "pdf":
            # ps2ascii converst pdf to ascii text
            # May have a potential formatting loss for unicode characters
            # return os.system(("ps2ascii %s") (fileName))
            try:
                return convertPDFToText(fileName), extension
            except Exception as e:
                return ''
        else:
            print('Unsupported format')
            return '', ''

    def preprocess(self, document):
        '''
            Information Extraction: Preprocess a document with the necessary POS tagging.
            Returns three lists, one with tokens, one with POS tagged lines, one with POS tagged sentences.
            Modules required: nltk
        '''

        try:
            # Try to get rid of special characters
            try:
                document = document.decode('ascii', 'ignore')
            except:
                document = document.encode('ascii', 'ignore')
                
            # Newlines are one element of structure in the data
            # Helps limit the context and breaks up the data as is intended in resumes - i.e., into points
            lines = [el.strip() for el in document.split(b"\n") if len(el) > 0]  # Splitting on the basis of newlines 
            lines = [nltk.word_tokenize(el.decode()) for el in lines if len(el) > 0]    # Tokenize the individual lines
            lines = [nltk.pos_tag(el) for el in lines]  # Tag them
            # Below approach is slightly different because it splits sentences not just on the basis of newlines, but also full stops 
            # - (barring abbreviations etc.)
            # But it fails miserably at predicting names, so currently using it only for tokenization of the whole document
            sentences = nltk.sent_tokenize(document.decode())    # Split/Tokenize into sentences (List of strings)
            sentences = [nltk.word_tokenize(sent) for sent in sentences]    # Split/Tokenize sentences into words (List of lists of strings)
            tokens = sentences
            sentences = [nltk.pos_tag(sent) for sent in sentences]    # Tag the tokens - list of lists of tuples - each tuple is (<word>, <tag>)
            # Next 4 lines convert tokens from a list of list of strings to a list of strings; basically stitches them together
            dummy = []
            for el in tokens:
                dummy += el
            tokens = dummy
            # tokens - words extracted from the doc, lines - split only based on newlines (may have more than one sentence)
            # sentences - split on the basis of rules of grammar
            return tokens, lines, sentences
        except Exception as e:
            print("An error occured during preprocessing \n", e)

    def tokenize(self, inputString):
        try:
            self.tokens, self.lines, self.sentences = self.preprocess(inputString)
            return self.tokens, self.lines, self.sentences
        except Exception as e:
            print("An error occured during tokenization\n", e)
            

    def getEmail(self, inputString, infoDict, debug=False): 
        '''
        Given an input string, returns possible matches for emails. Uses regular expression based matching.
        Needs an input string, a dictionary where values are being stored, and an optional parameter for debugging.
        Modules required: clock from time, code.
        '''

        email = None
        try:
            pattern = re.compile(r'\S*@\S*')
            matches = pattern.findall(inputString) # Gets all email addresses as a list
            email = matches
        except Exception as e:
            print("Error matching email\n", e)

        infoDict['email'] = email

        if debug:
            print("\n", pprint(infoDict), "\n")
            code.interact(local=locals())
        return email

    def getPhone(self, inputString, infoDict, debug=False):
        '''
            Given an input string, returns possible matches for phone numbers. Uses regular expression based matching.
            Needs an input string, a dictionary where values are being stored, and an optional parameter for debugging.
            Modules required: clock from time, code.
        '''

        number = None
        try:
            pattern = re.compile(r'([+(]?\d+[)\-]?[ \t\r\f\v]*[(]?\d{2,}[()\-]?[ \t\r\f\v]*\d{2,}[()\-]?[ \t\r\f\v]*\d*[ \t\r\f\v]*\d*[ \t\r\f\v]*)')
                # Understanding the above regex
                # +91 or (91) -> [+(]? \d+ -?
                # Metacharacters have to be escaped with \ outside of character classes; inside only hyphen has to be escaped
                # hyphen has to be escaped inside the character class if you're not incidication a range
                # General number formats are 123 456 7890 or 12345 67890 or 1234567890 or 123-456-7890, hence 3 or more digits
                # Amendment to above - some also have (0000) 00 00 00 kind of format
                # \s* is any whitespace character - careful, use [ \t\r\f\v]* instead since newlines are trouble
            match = pattern.findall(inputString)
            # match = [re.sub(r'\s', '', el) for el in match]
                # Get rid of random whitespaces - helps with getting rid of 6 digits or fewer (e.g. pin codes) strings
            # substitute the characters we don't want just for the purpose of checking
            match = [re.sub(r'[,.]', '', el) for el in match if len(re.sub(r'[()\-.,\s+]', '', el))>6]
                # Taking care of years, eg. 2001-2004 etc.
            match = [re.sub(r'\D$', '', el).strip() for el in match]
                # $ matches end of string. This takes care of random trailing non-digit characters. \D is non-digit characters
            match = [el for el in match if len(re.sub(r'\D','',el)) <= 15]
                # Remove number strings that are greater than 15 digits
            try:
                for el in list(match):
                    # Create a copy of the list since you're iterating over it
                    if len(el.split('-')) > 3: continue # Year format YYYY-MM-DD
                    for x in el.split("-"):
                        try:
                            # Error catching is necessary because of possibility of stray non-number characters
                            # if int(re.sub(r'\D', '', x.strip())) in range(1900, 2100):
                            if x.strip()[-4:].isdigit():
                                if int(x.strip()[-4:]) in range(1900, 2100):
                                    # Don't combine the two if statements to avoid a type conversion error
                                    match.remove(el)
                        except:
                            pass
            except:
                pass
            number = match
        except Exception as e:
            print("Error matching phone number\n", e)

        infoDict['phone'] = number

        if debug:
            print("\n", pprint(infoDict), "\n")
            code.interact(local=locals())
        return number

    def getName(self, inputString, infoDict, debug=False):
        '''
        Given an input string, returns possible matches for names. Uses regular expression based matching.
        Needs an input string, a dictionary where values are being stored, and an optional parameter for debugging.
        Modules required: clock from time, code.
        '''

        # Read Names from the file, reduce all to lower case for easy comparision [Name lists]
        names = open(settings.BASE_DIR / "constants/names.txt", "r").read().lower()
        # Lookup in a set is much faster
        names = set(names.split())
        

        othernames = []
        nameHits = []
        name = None

        try:
            tokens, lines, sentences = self.tokens, self.lines, self.sentences
            # Try a regex chunk parser
            # grammar = r'NAME: {<NN.*><NN.*>|<NN.*><NN.*><NN.*>}'
            grammar = r'NAME: {<NN.*><NN.*><NN.*>*}'
            # Noun phrase chunk is made out of two or three tags of type NN. (ie NN, NNP etc.) - typical of a name. {2,3} won't work, hence the syntax
            # Note the correction to the rule. Change has been made later.
            chunkParser = nltk.RegexpParser(grammar)
            all_chunked_tokens = []
            for tagged_tokens in lines:
                # Creates a parse tree
                if len(tagged_tokens) == 0: continue # Prevent it from printing warnings
                chunked_tokens = chunkParser.parse(tagged_tokens)
                all_chunked_tokens.append(chunked_tokens)
                for subtree in chunked_tokens.subtrees():
                    #  or subtree.label() == 'S' include in if condition if required
                    if subtree.label() == 'NAME':
                        for ind, leaf in enumerate(subtree.leaves()):
                            if leaf[0].lower() in names and 'NN' in leaf[1]:
                                # Case insensitive matching, as names have names in lowercase
                                # Take only noun-tagged tokens
                                # Surname is not in the name list, hence if match is achieved add all noun-type tokens
                                # Pick upto 3 noun entities
                                hit = " ".join([el[0] for el in subtree.leaves()[ind:ind+3]])
                                # Check for the presence of commas, colons, digits - usually markers of non-named entities 
                                if re.compile(r'[\d,:]').search(hit): continue
                                nameHits.append(hit)
                                # Need to iterate through rest of the leaves because of possible mis-matches
            # Going for the first name hit
            if len(nameHits) > 0:
                nameHits = [re.sub(r'[^a-zA-Z \-]', '', el).strip() for el in nameHits] 
                name = " ".join([el[0].upper()+el[1:].lower() for el in nameHits[0].split() if len(el)>0])
                othernames = nameHits[1:]

        except Exception as e:
            print(traceback.format_exc())
            print(e)         

        infoDict['name'] = name
        infoDict['othernames'] = othernames

        if debug:
            print("\n", pprint(infoDict), "\n")
            code.interact(local=locals())
        return name, othernames
    
    def getExperience(self, inputString, infoDict, debug=True):
        experience=[]
        try:
            for sentence in self.lines:#find the index of the sentence where the degree is find and then analyse that sentence
                    sen=" ".join([words[0].lower() for words in sentence]) #string of words in sentence
                    if re.search('experience',sen):
                        sen_tokenised= nltk.word_tokenize(sen)
                        tagged = nltk.pos_tag(sen_tokenised)
                        entities = nltk.chunk.ne_chunk(tagged)
                        for subtree in entities.subtrees():
                            for leaf in subtree.leaves():
                                if leaf[1]=='CD':
                                    experience=leaf[0]
        except Exception as e:
            print(traceback.format_exc())
            print(e) 
        if experience:
            infoDict['experience'] = experience
        else:
            infoDict['experience'] = 0
        if debug:
            print("\n", pprint(infoDict), "\n")
            code.interact(local=locals())
        return experience
    

    def getQualification(self, inputString, infoDict, D1, D2):
        #key=list(qualification.keys())
        qualification={'school': '', 'year': ''}
        nameofinstitutes = open(settings.BASE_DIR / 'constants/nameofinstitutes.txt', 'r').read().lower() #open file which contains keywords like institutes, university usually fond in institute names
        nameofinstitutes = set(nameofinstitutes.split())
        instiregex=r'INSTI: {<DT.>?<NNP.*>+<IN.*>?<NNP.*>?}'
        chunkParser = nltk.RegexpParser(instiregex)
        
        try:           
            index = []
            line = [] # saves all the lines where it finds the word of that education
            for ind, sentence in enumerate(self.lines): # find the index of the sentence where the degree is find and then analyse that sentence
                sen = " ".join([words[0].lower() for words in sentence]) # string of words
                if re.search(D1, sen) or re.search(D2, sen):
                    index.append(ind)  # list of all indexes where word Ca lies
            if index: # only finds for Ca rank and CA year if it finds the word Ca in the document
                
                for indextocheck in index: # checks all nearby lines where it founds the degree word.ex-'CA'
                    for i in [indextocheck, indextocheck+1]: # checks the line with the keyword and just the next line to it
                        try:
                            try:
                                wordstr=" ".join(words[0] for words in self.lines[i]) # string of that particular line
                            except:
                                wordstr = ""
                            #if re.search(r'\D\d{1,3}\D',wordstr.lower()) and qualification['rank']=='':
                                    #qualification['rank']=re.findall(r'\D\d{1,3}\D',wordstr.lower())
                                    #line.append(wordstr)
                            if re.search(r'\b[21][09][8901][0-9]', wordstr.lower()) and qualification['year'] == '':
                                    qualification['year'] = re.findall(r'\b[21][09][8901][0-9]', wordstr.lower())
                                    line.append(wordstr)
                            chunked_line = chunkParser.parse(self.lines[i]) # regex chunk for searching univ name
                            for subtree in chunked_line.subtrees():
                                if subtree.label() == 'INSTI':
                                    for ind, leaves in enumerate(subtree):
                                        if leaves[0].lower() in nameofinstitutes and leaves[1] == 'NNP' and qualification['school'] == '':
                                            qualification['school'] = ' '.join([words[0]for words in subtree.leaves()])
                                            line.append(wordstr)
                                
                        except Exception as e:
                            print(traceback.format_exc())
            
            if qualification['school']: 
                infoDict[f'{D1}_school'] = str(qualification['school'])
                
            if qualification['year']:
                infoDict[f'{D1}_year'] = int(qualification['year'][0])
                
            infoDict[f'{D1}_degree'] = list(set(line))
        except Exception as e:
            print(traceback.format_exc())
            print(e) 


    def Qualification(self, inputString, infoDict, debug=False):
        degree = []
        
        with open(settings.BASE_DIR / 'constants/qualifications.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                self.getQualification(self.inputString, infoDict, row[0], row[1])
                if infoDict.get(f'{row[0]}_degree'):
                    degree.append(row[0])
                    
        if degree:
            infoDict['degrees'] = degree
        else:
            infoDict['degrees'] = "NONE"
        
        if debug:
            code.interact(local=locals())
        return infoDict['degrees']
