#======================================================================================
#  3D Slicer [1] plugin that uses elastix toolbox [2] Plugin for Automatic Cervical   # 
#  SPine Image Segmentation and other useful features extraction[3]                   #
#  More info can be found at [3,4 and 5]                                              #
#  Sample vertebra datasets can be downloaded using Slicer Datastore module           #
#                                                                                     #
#  Contributers: Ibraheem Al-Dhamari,  idhamari@uni-koblenz.de                        #
#  [1] https://www.slicer.org                                                         #
#  [2] http://elastix.isi.uu.nl                                                       #
#  [3] Ibraheem AL-Dhamari, Sabine Bauer, Eva Keller and Dietrich Paulus, (2019),     #
#      Automatic Detection Of Cervical Spine Ligaments Origin And Insertion Points,   #
#      IEEE International Symposium on Biomedical Imaging (ISBI), Venice, Italy.      #
#  [4] Ibraheem Al-Dhamari, Sabine Bauer, Dietrich Paulus, (2018), Automatic          #
#      Multi-modal Cervical Spine Image Atlas Segmentation Using Adaptive Stochastic  #
#      Gradient Descent, Bildverarbeitung feur die Medizin 2018 pp 303-308.            #  
#  [5] https://mtixnat.uni-koblenz.de                                                 #
#                                                                                     #
#  Updated: 14.2.2019                                                                 #    
#                                                                                     #  
#======================================================================================

import os, re , datetime, time ,shutil, unittest, logging, zipfile, urllib2, stat,  inspect
import sitkUtils, sys ,math, platform, subprocess  
import numpy as np, SimpleITK as sitk
import vtkSegmentationCorePython as vtkSegmentationCore
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *   
from copy import deepcopy
from collections import defaultdict
from os.path import expanduser
from os.path import isfile
from os.path import basename
from PythonQt import BoolResult
from shutil import copyfile
from decimal import *
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.dummy import Process  

import SegmentStatistics
import Elastix
import CervicalVertebraTools

#TODO:
# size, change parameters, change locations
# wrong position, wrong results for a group.

# cleaning 
# vertebra info parallel
# extract scaled model
# remove temporary node and files
# test with user input


# parallel implementation
# compare parallel to sequential time
# locating vertebrae 
# public module
 
# Public version: without detailed segmentation.  
# Test on Windows
#    e.g. open folder 



#   Registration download all stuff for both registration and segmentation.
#   use registration module and commong functions:  
#   Remove inverted transform, it was using in case switching moving and fixed 
# Later:
# - Checking if all above are needed 
# - Cleaning, optimizing, commenting.  
# - Testing in both Windows and Linux. 
# - Supporting DICOM. 
# - Supporting illegal filename.  
# - Using  SlierElastix binaries.   
# - Visualizing the interimediate steps. 
# 
#  
# Terminology
#  img         : ITK image 
#  imgNode     : Slicer Node
#  imgPath     : wholePath + Filename
#  imgFnm      : Filename without the path and the extension
#  imgFileName : Filename without the path

#===================================================================
#                           Main Class
#===================================================================

class CervicalSpineTools(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        parent.title = "Cervical Spine Tools"
        parent.categories = ["VisSimTools"]
        parent.dependencies = []
        parent.contributors = ["Ibraheem Al-Dhamari" ]
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        #TODO: add sponsor
        parent.acknowledgementText = " This work is sponsored by ................ "
        self.parent = parent
  #end def init
#end class vertebraSeg

    
#===================================================================
#                           Main Widget
#===================================================================
class CervicalSpineToolsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  #VTl = CervicalVertebraTools.CervicalVertebraToolsLogic()
  def setup(self):
    print(" ")
    print("=======================================================")   
    print("   VisSim Cervical Spine Tools               ")
    print("=======================================================")           
        
    ScriptedLoadableModuleWidget.setup(self)
    
    # to access logic class functions and setup global variables
    # Set default VisSIm location in the user home 
    #TODO: add option user-defined path when installed first time
    self.logic = CervicalSpineToolsLogic()
    self.VTl = CervicalVertebraTools.CervicalVertebraToolsLogic()    
    #=================================================================
    #                     Create the GUI interface
    #=================================================================   
    # Create main collapsible Button 
    self.mainCollapsibleBtn = ctk.ctkCollapsibleButton()
    self.mainCollapsibleBtn.setStyleSheet("ctkCollapsibleButton { background-color: DarkSeaGreen  }")
    self.mainCollapsibleBtn.text = "VisSim Cervical Spine Tools"
    self.layout.addWidget(self.mainCollapsibleBtn)
    self.mainFormLayout = qt.QFormLayout(self.mainCollapsibleBtn)
  
    # Create input Volume Selector
    self.inputSelectorCoBx = slicer.qMRMLNodeComboBox()
    self.inputSelectorCoBx.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelectorCoBx.setFixedWidth(200)
    self.inputSelectorCoBx.selectNodeUponCreation = True
    self.inputSelectorCoBx.addEnabled = False
    self.inputSelectorCoBx.removeEnabled = False
    self.inputSelectorCoBx.noneEnabled = False
    self.inputSelectorCoBx.showHidden = False
    self.inputSelectorCoBx.showChildNodeTypes = False
    self.inputSelectorCoBx.setMRMLScene( slicer.mrmlScene )
    self.inputSelectorCoBx.setToolTip("select the input image")
    self.mainFormLayout.addRow("Input image: ", self.inputSelectorCoBx)

    # use qtcombobox
    self.vILbl = qt.QLabel()
    self.vILbl.setText("Which Vertebra? 1-7")        
    self.vILbl.setFixedHeight(20)
    self.vILbl.setFixedWidth(150)
    
    #TODO: include head and shoulders
    self.vtIDCoBx = qt.QComboBox()
    self.vtIDCoBx.addItems(["C1","C2","C3","C4","C5","C6","C7"])
    self.vtIDCoBx.setCurrentIndex(2)
    self.vtIDCoBx.setFixedHeight(20)
    self.vtIDCoBx.setFixedWidth(100)        
    #self.vtIDCoBx.setReadOnly(False) # The point can only be edited by placing a new Fiducial
    # if changed , the default value will change  
    self.vtIDCoBx.connect("currentIndexChanged(int)", self.onVtIDCoBxChange)                  
    #self.mainFormLayout.addRow( self.vILbl,  self.vtIDCoBx )        
      
    # Create a textbox for vertebra location
    # TODO activate input IJK values as well
    Pt = [0,0,0]
    self.inputPointEdt = qt.QLineEdit()
    self.inputPointEdt.setFixedHeight(20)
    self.inputPointEdt.setFixedWidth(100)
    self.inputPointEdt.setText(str(Pt))
    self.inputPointEdt.connect("textChanged(QString)", self.onInputPointEdtChanged)                                  
    #self.inputPointEdt.connect("textEdited(str)", self.onInputPointEdtEdited)                                  

    self.mainFormLayout.addRow( self.inputPointEdt, self.vtIDCoBx)    

    # Add check box for extracting ligaments points 
    self.ligPtsChkBx = qt.QCheckBox("Ligaments points")
    self.ligPtsChkBx.checked = True
    self.ligPtsChkBx.stateChanged.connect(self.onLigPtsChkBxChange)
    self.mainFormLayout.addRow(self.ligPtsChkBx)

    # Create a time label
    self.timeLbl = qt.QLabel("  Time: 00:00")
    self.timeLbl.setFixedWidth(500)   
    self.tmLbl = self.timeLbl
    
    # Create a button to run segmentation
    self.applyBtn = qt.QPushButton("Run")
    self.applyBtn.setFixedHeight(50)
    self.applyBtn.setFixedWidth (150)
    self.applyBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
    self.applyBtn.toolTip = ('How to use:' ' Load an images into Slicer. Pick vertebra locations using the buttons and the Slicer Fiducial tool ')
    self.applyBtn.connect('clicked(bool)', self.onApplyBtnClick)
    self.mainFormLayout.addRow(self.applyBtn, self.timeLbl)
    self.runBtn = self.applyBtn

    # Create a button to display result folder
    self.openResultFolderBtn = qt.QPushButton("open output folder")
    self.openResultFolderBtn.setFixedHeight(20)
    self.openResultFolderBtn.setFixedWidth (150)
    self.openResultFolderBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
    self.openResultFolderBtn.toolTip = ('Scale model and points to 1 mm and translate them to the model center of mass ')
    self.openResultFolderBtn.connect('clicked(bool)', self.onOpenResultFolderBtnClick)
    
    self.mainFormLayout.addRow(self.openResultFolderBtn)

    self.layout.addStretch(1) # Collapsible button is held in place when collapsing/expanding.
    lm = slicer.app.layoutManager();    lm.setLayout(2)

  def cleanup(self):#nothing to do 
    pass
  #enddef


  #------------------------------------------------------------------------
  #                        Vertebra Selection
  #------------------------------------------------------------------------
  def onVtIDCoBxChange(self):
      self.inputVolumeNode=self.inputSelectorCoBx.currentNode()
      self.vtID = self.vtIDCoBx.currentIndex + 1   
      self.logic.inputVolumeNode  =  self.inputVolumeNode 
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      self.logic.inputFiducialNode = None
      for f in nodes:
          if ((f.GetName() == self.inputVolumeNode.GetName()+"_vtLocations") ):
             #replace  current 
             print("inputFiducialNode exist")
             self.logic.inputFiducialNode = f  
             newNode= False
            #endif
      #endfor    
      self.VTl.setVtID(self.vtID,self.logic.inputVolumeNode ,self.logic.inputFiducialNode )  
      self.VTl.locateVertebra(self.inputVolumeNode, self.vtID, self.inputPointEdt)    
      #self.onInputFiducialBtnClick()
  #enddef

  def onInputPointEdtChanged(self,point):
      self.vtID = self.vtIDCoBx.currentIndex + 1   
      self.VTl.setVtIDfromEdt(point, self.vtID)
  #enddef
    
  # resample or not  
  # TODO: automate the process
  def onHrChkBxChange(self):      
      self.logic.setHrChk(self.hrChkBx.checked)
  #enddef

  # extract ligaments points 
  def onLigPtsChkBxChange(self):      
      nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
      self.VTl.setLigChk(self.ligPtsChkBx.checked,nodes)
  #enddef
  
  def onApplyBtnClick(self):
      #check if C1,C4 and C7 points are selected
      self.runBtn.setText("...please wait")
      self.runBtn.setStyleSheet("QPushButton{ background-color: red  }")
      slicer.app.processEvents()
      self.stm=time.time()
      print("time:" + str(self.stm))
      self.timeLbl.setText("                 Time: 00:00")
    
      self.vtID = self.vtIDCoBx.currentIndex + 1
      self.inputNode = self.inputSelectorCoBx.currentNode()
      pointSelected = self.inputPointEdt.text =="[0,0,0]"
      try: 
            if  (not self.inputNode is None) and (not pointSelected) and (not self.logic.inputFiducialNode is None):
                 # create an option to use IJK point or fidicual node
                 # inputImage, FiducialPoints, isExteranl 
                 self.logic.run( self.inputSelectorCoBx.currentNode(),self.logic.inputFiducialNode ,False)         
  
            else:
                print("C1,C4 and C7 points are not selected !")   
      except Exception as e:
                print("STOPPED: error in input")
                print(e)
      #endtry        
      self.etm=time.time()
      tm=self.etm - self.stm
      self.timeLbl.setText("Time: "+str(tm)+"  seconds")
      self.runBtn.setText("Run")
      self.runBtn.setStyleSheet("QPushButton{ background-color: DarkSeaGreen  }")
      slicer.app.processEvents()
                
  #enddef
       
  def onOpenResultFolderBtnClick(self):
      output = expanduser("~")+",VisSimTools"   + ",outputs"
      output = os.path.join(*output.split(","))
      self.VTl.openResultsFolder(output)
  #enddef
#===================================================================
#                           Logic
#===================================================================
class CervicalSpineToolsLogic(ScriptedLoadableModuleLogic):

  ElastixLogic = Elastix.ElastixLogic()
  ElastixBinFolder = ElastixLogic.getElastixBinDir()
  VTl = CervicalVertebraTools.CervicalVertebraToolsLogic()
  vtVars = VTl.setGlobalVariables(True)
  VTl.vtVars =vtVars
  
  # Check if image is valid
  def hasImageData(self,inputVolumeNode):
    #check input image 
    if not inputVolumeNode:
      logging.debug('hasImageData failed: no input volume node')
      return False
    if inputVolumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in input volume node')
      return False
    return True
  #enddef


  def getAllVertebraePoints(self,vtIDsLst,inputFiducialNode):
                
      #TODO: test on all images, the direction should be involved.
      print("Spine: Compute vertebra locations !")
      if ((vtIDsLst[6][0]!=0) and (vtIDsLst[3][0]!=0) and (vtIDsLst[0][0]!=0)) : 
         # we need: 1,4 and 7
         # compute displacement between C4 and C1
         v1x= (vtIDsLst[3][0]-vtIDsLst[0][0])/4 ; print(v1x)
         v1y= (vtIDsLst[3][1]-vtIDsLst[0][1])/4 ; print(v1y)
         v1z= (vtIDsLst[3][2]-vtIDsLst[0][2])/4 ; print(v1z)
         
         # C3 location
         vtIDsLst[2]=[vtIDsLst[3][0]-v1x , vtIDsLst[3][1]-v1y , vtIDsLst[3][2]-v1z]
         inputFiducialNode.AddFiducialFromArray(vtIDsLst[2])
         inputFiducialNode.SetNthFiducialLabel(4, "C3")

         ## C2 location
         #vtIDsLst[1]=[vtIDsLst[2][0]-v1x , vtIDsLst[2][1]-v1y , vtIDsLst[2][2]-v1z]
         #self.inputFiducialNode.AddFiducialFromArray(vtIDsLst[1])
         #self.inputFiducialNode.SetNthFiducialLabel(4, "C2") # note that 4 is the index of last one added so far

         # compute displacement between C7 and C4
         v2x= (vtIDsLst[6][0]-vtIDsLst[3][0])/4
         v2y= (vtIDsLst[6][1]-vtIDsLst[3][1])/4
         v2z= (vtIDsLst[6][2]-vtIDsLst[3][2])/4
         
         # C5 location
         vtIDsLst[4]=[vtIDsLst[3][0]+v1x , vtIDsLst[3][1]+v1y , vtIDsLst[3][2]+v1z]
         inputFiducialNode.AddFiducialFromArray(vtIDsLst[4])
         inputFiducialNode.SetNthFiducialLabel(5, "C5")
         
         # C6 location
         vtIDsLst[5]=[vtIDsLst[4][0]+v1x , vtIDsLst[4][1]+v1y , vtIDsLst[4][2]+v1z]
         inputFiducialNode.AddFiducialFromArray(vtIDsLst[5])
         inputFiducialNode.SetNthFiducialLabel(6, "C6")

      #endif
      return vtIDsLst
  #enddef
         

  def  run( self, inputVolumeNode, inputFiducialNode , isExternalCall):

       outputPaths =[]
       intputCropPaths  =[]
       inputPoints = []
       modelCropPaths = []
       vtIDsLst = []

       rng= 7 # number of vertebra
       for j in range(7):
           vtIDsLst.append([0,0,0])
           intputCropPaths.append("")
           inputPoints.append([0,0,0])
       #endfor    
       print(inputFiducialNode.GetNumberOfFiducials())
       for j in range(inputFiducialNode.GetNumberOfFiducials()):
           l= inputFiducialNode.GetNthFiducialLabel(j)
           print(l);
           print(l[1]);
           k = int(l[1])
           inputFiducialNode.GetNthFiducialPosition(j,vtIDsLst[k-1])
       #endfor       
       vtIDsLst =  self.getAllVertebraePoints(vtIDsLst,inputFiducialNode)       
  
       print("get vertebra information")
       tableName =  inputVolumeNode.GetName()+"_tbl"
       resultsTableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode")
       resultsTableNode.SetName(tableName)
       resultsTableNode.AddEmptyRow()    
       resultsTableNode.GetTable().GetColumn(0).SetName("Vertebra")
       resultsTableNode.AddColumn()
       resultsTableNode.GetTable().GetColumn(1).SetName("Volume mm3")
       resultsTableNode.AddColumn()
       resultsTableNode.GetTable().GetColumn(2).SetName("CoM X")
       resultsTableNode.AddColumn()
       resultsTableNode.GetTable().GetColumn(3).SetName("CoM Y")
       resultsTableNode.AddColumn()
       resultsTableNode.GetTable().GetColumn(4).SetName("CoM Z")
       self.resultsTableNode = resultsTableNode
       
       for i in range(rng):
           #get other points 
           #create a list from the points
           vtID = i+1
           outputPath = self.vtVars['outputPath']+","+inputVolumeNode.GetName()+"_C"+str(vtID)
           outputPath = os.path.join(*outputPath.split(","))
           outputPaths.append( outputPath) 
           modelCropPath       = self.vtVars['modelPath']+ ',Default' +",Mdl" + self.vtVars['Styp']+ str(vtID)        +self.vtVars['imgType'] 
           modelCropPath       = os.path.join(*modelCropPath.split(","))
           modelCropPaths.append(modelCropPath)  
           if not os.path.exists(outputPaths[i]):
              os.makedirs(outputPaths[i])
           #endif
           print(modelCropPaths[i])
           print(outputPaths[i])
       #endfor 
       self.inputVolumeNode = inputVolumeNode
       self.inputFiducialNode = inputFiducialNode
       self.outputPaths =  outputPaths
       self.modelCropPaths =  modelCropPaths       
       self.inputPoints =  inputPoints       
       self.intputCropPaths =  intputCropPaths       

       # try parallel but slicer crash
       # try if we collect information then run popen
       """
       i=range(rng)
       pool = ThreadPool(9)
       b=pool.map(self.runCroppingAll,i)
       pool.close()
       pool.join()
       """
       #---------------------  process ------------------------------------           
       for i in range (rng):
           vtID = i+1 
           self.runCroppingAll(i)
           self.runElastixAll(i)
           vtTransformNode = self.runTransformixAll(i)

           resultSegNodeName       = self.inputVolumeNode.GetName() + "_Seg_C"+str(vtID)           
           modelCropSegPath    = self.vtVars['modelPath'] + self.vtVars['segT']+",Mdl"+self.vtVars['Styp']+ str(vtID)+ self.vtVars['sgT'] +self.vtVars['imgType'] 
           modelCropSegPath    =   os.path.join(*modelCropSegPath.split(","))
           print(self.vtVars['segT'])
           print(self.vtVars['sgT'])
           print(modelCropSegPath)

           
           [success, vtResultSegNode] = slicer.util.loadSegmentation(modelCropSegPath, returnNode = True)
           vtResultSegNode.SetName(resultSegNodeName)
           vtResultSegNode.SetAndObserveTransformNodeID(vtTransformNode.GetID()) # movingAllMarkupNode should be loaded, the file contains all points
           slicer.vtkSlicerTransformLogic().hardenTransform(vtResultSegNode) 
           vtResultSegNode.CreateClosedSurfaceRepresentation() 

           if self.VTl.s2b(self.vtVars['ligChk']):            
              print ("************  Transform Ligaments Points **********************")
              modelCropImgLigPtsPath = self.vtVars['modelPath'] +self.vtVars['vtPtsLigDir']+","+self.vtVars['Styp']+ str(vtID)+self.vtVars['vtPtsLigSuff']+".fcsv"
              modelCropImgLigPtsPath        = os.path.join(*modelCropImgLigPtsPath.split(","))
              resultLigPtsNodeName =  self.inputVolumeNode.GetName() + "_LigPts_C"+str(vtID)
              [success, vtResultLigPtsNode] = slicer.util.loadMarkupsFiducialList  (modelCropImgLigPtsPath, returnNode = True)
              vtResultLigPtsNode.GetDisplayNode().SetTextScale(1)
              vtResultLigPtsNode.GetDisplayNode().SetSelectedColor(1,0,0)           
              vtResultLigPtsNode.SetName(resultLigPtsNodeName)
              vtResultLigPtsNode.SetAndObserveTransformNodeID(vtTransformNode.GetID()) # movingAllMarkupNode should be loaded, the file contains all points
              slicer.vtkSlicerTransformLogic().hardenTransform(vtResultLigPtsNode) # apply the transform
              # needed in extract scaled model
              self.vtResultLigPtsNode = vtResultLigPtsNode
           #endif 

           print ("************  get Vertebra Info  **********************")
           self.getVertebraInfoAll( i )
       #endfor

       self.resultsTableNode.RemoveRow(self.resultsTableNode.GetNumberOfRows()-1)   
       #segStatLogic = SegmentStatistics.SegmentStatisticsLogic()
       #segStatLogic.showTable(resultsTableNode)
       slicer.app.layoutManager().setLayout( slicer.modules.tables.logic().GetLayoutWithTable(slicer.app.layoutManager().layout))
       slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(self.resultsTableNode.GetID())
       slicer.app.applicationLogic().PropagateTableSelection()
     
       self.vtVars['segNodeCoM']= self.VTl.vtVars['segNodeCoM']
       self.vtResultSegNode = vtResultSegNode
       #slicer.mrmlScene.RemoveNode(croppedNode )

  #enddef


  def runCroppingAll(self,i):
      vtID = i+1
      print("------------ cropping process: " +str(i))
      # try crop in parallel:   
      for j in range (self.inputFiducialNode.GetNumberOfFiducials() ):
          if self.inputFiducialNode.GetNthFiducialLabel(j)==("C"+str(vtID)):
             break
          #endif
      #endfor
      self.inputPoints[i]=self.VTl.ptRAS2IJK(self.inputFiducialNode,j,self.inputVolumeNode)
      print(self.inputPoints[i])
      self.intputCropPaths[i]=self.VTl.runCropping(self.inputVolumeNode, self.inputPoints[i],  vtID , self.vtVars['croppingLength'], self.vtVars['RSxyz'],self.vtVars['hrChk'] )
      
      print("ii = " +str(i)+ "  img :"+ self.intputCropPaths[i]          )
      print("------------ cropping process: " +str(i)+"  ...complete")
  #enddef

  def runElastixAll(self,i):
      vtID = i+1
      print("------------ elastix process: " +str(i))
      #self.runElastix(self.vtVars['elastixBinPath'], self.intputCropPaths[i], self.modelCropPaths[i], self.outputPaths[i], self.vtVars['parsPath'] ,self.vtVars['noOutput'], "674")
      self.VTl.runElastix(self.vtVars['elastixBinPath'], self.intputCropPaths[i], self.modelCropPaths[i], self.outputPaths[i], self.vtVars['parsPath'] ,self.vtVars['noOutput'], "674")

      print("------------ elastix process: " +str(i)+"  ...complete")
  #enddef

  def runTransformixAll(self,i):
      vtID = i+1
      resTransPath  = os.path.join(self.outputPaths[i] ,"TransformParameters.0.txt")
      resOldDefPath = os.path.join(self.outputPaths[i] , "deformationField"+self.vtVars['imgType'])
      resDefPath    = os.path.join(self.outputPaths[i] , self.inputVolumeNode.GetName()+"C"+str(vtID)+"_dFld"+self.vtVars['imgType'])
      #remove old result files:
      if os.path.isfile(resOldDefPath):
         os.remove(resOldDefPath) 
      if os.path.isfile(resDefPath):
         os.remove(resDefPath)
        
      #os.remove(resOldDefPath)
      #os.remove(resDefPath)

      print("------------ transformix process: " +str(i))
      #self.runTransformix(self.vtVars['transformixBinPath'] ,self.modelCropPaths[i], self.outputPaths[i], resTransPath, self.vtVars['noOutput'], "1254")
      self.VTl.runTransformix(self.vtVars['transformixBinPath'] ,self.modelCropPaths[i], self.outputPaths[i], resTransPath, self.vtVars['noOutput'], "1254")

      os.rename(resOldDefPath,resDefPath)
      resultTransformNodeName = self.inputVolumeNode.GetName()+ "_Transform_C"+str(vtID)
      [success, vtTransformNode] = slicer.util.loadTransform(resDefPath, returnNode = True)
      vtTransformNode.SetName(resultTransformNodeName)
      print("------------ transformix process: " +str(i)+"  ...complete")
      return vtTransformNode
  #enddef
                
  def getVertebraInfoAll(self,i):
      vtID = i+1
      segName = self.inputVolumeNode.GetName() + "_Seg_C"+str(vtID)  
      segNode = slicer.util.getNode(segName)
      masterName = self.inputVolumeNode.GetName() + "_C"+str(vtID)+"_crop"
      masterNode = slicer.util.getNode(masterName)

      self.resultsTableNode = self.VTl.getVertebraInfo( segNode, masterNode, vtID, self.resultsTableNode)
  #enddef
  
  def rmvSlicerNode(self,node):
    slicer.mrmlScene.RemoveNode(node)
    slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
    slicer.mrmlScene.RemoveNode(node.GetStorageNode())
  #enddef
                              
#===================================================================
#                           Test
#===================================================================
class CervicalSpineToolsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  logic =  CervicalSpineToolsLogic()
  #VTl  = CervicalVertebraTools.CervicalVertebraToolsLogic()
  #VTl.setGlobalVariables(True)

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)
    #self.vtVars = self.logic.setGlobalVariables(True)
        

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.testSlicerCervicalSpineTools()

  def testSlicerCervicalSpineTools(self):
 
    # optimize run in parallel 
    self.delayDisplay("Starting the test")
    self.stm=time.time()
    print("time:" + str(self.stm))

    #msgbox for testing
    

    tstImg = 1 # 1 =CT, 2 = MR 
    if tstImg ==1:
       imgWebLink = "https://cloud.uni-koblenz-landau.de/s/Mb6JHLdWw5MEPB2/download"
       fnm = os.path.join(*(self.logic.vtVars['outputPath'] +",imgCT"+self.logic.vtVars['imgType']).split(","))
       #  CT: define a markup with all locations  
       c1p = [-5.507 ,  -20.202 , -18.365 ]
       c2p = [-1.169  , -20.089 , -45.021 ]
       c4p = [ 0.390  , -11.754 , -74.194 ]
       c7p = [ 0.390  , -26.445 ,-115.821 ]
    else:
       imgWebLink = "https://cloud.uni-koblenz-landau.de/s/ieyDfHpCjHNpZXi/download"
       fnm = os.path.join(*(self.logic.vtVars['outputPath'] +",imgMR"+self.logic.vtVars['imgType']).split(","))
       # MR: define a markup with all locations     
       c1p = [  1.062  ,  53.364 ,  145.951 ]
       c2p = [ -0.408  ,  44.283 ,  122.994 ]
       c4p = [ -0.408  ,  36.107 ,   89.941 ]
       c7p = [ -0.408  ,   3.439 ,   54.432 ]
    #endif
        
    # don't download if already downloaded                       
    if not os.path.exists(fnm):
       try:         
           print("Downloading vertebra sample image ...")
           import urllib
           urllib.urlretrieve (imgWebLink ,fnm )
       except Exception as e:
              print("Error: can not download sample file  ...")
              print(e)   
              return -1
       #end try-except 
    #endif
    
    # remove old nodes 
    nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
    for f in nodes:
       if ((f.GetName() == "VertebraLocationPoint") ):
           slicer.mrmlScene.RemoveNode(f)
       #endif
    #endfor 
    nodes = slicer.util.getNodesByClass('vtkScalarVolumeNode')
    for f in nodes:
       if (f.GetName() ==  "imgA"):
           slicer.mrmlScene.RemoveNode(f)
       #endif
    #endfor 
    
     
    [success, inputVolumeNode] = slicer.util.loadVolume( fnm, returnNode=True)
    
    inputFiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
    inputFiducialNode.CreateDefaultDisplayNodes()
    #TODO: change the name to points 
    inputFiducialNode.SetName("VertebraLocationPoint")  
    inputFiducialNode.AddFiducialFromArray(c1p)
    inputFiducialNode.SetNthFiducialLabel(0, "C1")
    inputFiducialNode.AddFiducialFromArray(c2p)
    inputFiducialNode.SetNthFiducialLabel(1, "C2")
    inputFiducialNode.AddFiducialFromArray(c4p)
    inputFiducialNode.SetNthFiducialLabel(2, "C4")
    inputFiducialNode.AddFiducialFromArray(c7p)
    inputFiducialNode.SetNthFiducialLabel(3, "C7")

    # call run with the downloaded image and the locations
    isExt = True
    # run( self,         inputVolumeNode, inputFiducialNode      , isExternalCall):
    self.logic.run(inputVolumeNode, inputFiducialNode , isExt )
    
    self.etm=time.time()
    tm=self.etm - self.stm
    print("Time: "+str(tm)+"  seconds")

    self.delayDisplay('Test passed!')
  #enddef

 