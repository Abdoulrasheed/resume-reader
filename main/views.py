from .parser import Parse
from django.conf import settings 
from rest_framework import status
from .serializers import FileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.storage import FileSystemStorage
from rest_framework.parsers import MultiPartParser, FormParser

class FileView(APIView):
  parser_classes = (MultiPartParser, FormParser)
  
  def post(self, request, *args, **kwargs):
    file_serializer = FileSerializer(data=request.data)
    fs = FileSystemStorage()
    
    if file_serializer.is_valid():
      obj = file_serializer.save()
      uploaded_file_path = fs.path(obj.file.url.split("/")[2])
      parser = Parse(verbose=False, f=uploaded_file_path)
      print(parser.result)
      return Response(parser.result, status=status.HTTP_201_CREATED)
    else:
      return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)