# -- coding: utf-8 --
from __future__ import print_function, unicode_literals

import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import traceback
from StringIO import StringIO

import NodegraphAPI
import Nodes3DAPI.RenderNodeUtil
from Katana import FarmAPI, QtCore, UI4, version

# Katana 3.1 changed from using Qt4 to Qt5, so we import the widgets into the current namespace to maintain backwards compatibility.
# We are importing from PyQt# instead of Katana so we are able to directly import the symbols.
try:
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout, QWidget
except ImportError:
    from PyQt4.QtGui import QCheckBox, QComboBox, QFont, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout, QWidget

from deadline_katana.scene import get_output_nodes

integrationInfoKeyValues = {}
submissionInfo = None

stickySettingWidgets = {
        "Department": "departmentWidget",
        "Comment": "commentWidget",
        "Pool": "poolsWidget",
        "SecondaryPool": "secondPoolsWidget",
        "Group": "groupWidget",
        "Priority": "priorityBox",
        "TaskTimeout": "taskTimeoutBox",
        "ConcurrentTasks": "concurrentTasksWidget",
        "LimitConcurrentTasksToNumberOfCpus": "limitTasksSlaveLimit",
        "MachineLimit": "machineLimitWidget",
        "IsBlacklist": "isBlackListWidget",
        "MachineList": "machineListWidget",
        "LimitGroups": "limitsWidget",
        "OnJobComplete": "onJobCompleteWidget",
        "InitialStatus": "submitSuspendedWidget",

        "SubmitScene": "submitSceneBox",
        "UseWorkingDirectory": "useWorkingDirectory",
        "IncludeImageWrite": "includeImageWrite",
        "IsFrameDependent": "frameDependent",
    }

stickyWidgetLoadFunctions = {
    QComboBox: ( lambda uiObject, val: uiObject.setCurrentIndex( max( uiObject.findText( val ), 0 ) ) ),
    QLineEdit: ( lambda uiObject, val: uiObject.setText( val ) ),
    QSpinBox: ( lambda uiObject, val: uiObject.setValue( val ) ),
    QCheckBox: ( lambda uiObject, val: uiObject.setChecked( val ) ),
}
stickyWidgetSaveFunctions = {
    QComboBox: ( lambda uiObject: unicode(uiObject.currentText()) ),
    QLineEdit: ( lambda uiObject: unicode( uiObject.text()) ),
    QSpinBox: ( lambda uiObject: uiObject.value() ),
    QCheckBox: ( lambda uiObject: uiObject.isChecked() ),
}

def PopulateSubmitter( gui ):
    """
    This function populates an instance of DeadlineTab with the UI controls that make up the submission dialog.
    This tab is instantiated by Katana every time the user selects "Tabs -> Thinkbox -> Submit to Deadline" from the
    menu bar in Katana.

    Essentially, this function serves as a deferred __init__ implementation for the tab class that can be easily updated
    via the Deadline repository.

    :param gui: An instance of DeadlineTab from the Client folder. The instance gets created upon selecting the
                "Deadline" tab option in Katana. The tab class itself is defined in the Client file (deployed to
                localappdata/.../katanasubmitter/tabs directory) and is a skeleton class that invokes this
                function to populate the tab with UI controls and assign them to attributes of the tab instance.
    """
    global submissionInfo
    print( "Grabbing submitter info..." )
    try:
        stringSubInfo = CallDeadlineCommand( [ "-prettyJSON", "-GetSubmissionInfo", "Pools", "Groups", "MaxPriority", "UserHomeDir", "RepoDir:submission/Katana/Main", "RepoDir:submission/Integration/Main", ], useDeadlineBg=True )
        output = json.loads( stringSubInfo, encoding="utf-8" )
    except:
        print( "Unable to get submitter info from Deadline:\n\n" + traceback.format_exc() )
        raise
    if output[ "ok" ]:
        submissionInfo = output[ "result" ]
    else:
        print( "DeadlineCommand returned a bad result and was unable to grab the submitter info.\n\n" + output[ "result" ] )
        raise ValueError( output[ "result" ] )
    # Create a widget with a vertical box layout as a container for widgets to include in the tab
    scrollWidget = QWidget()
    scrollLayout = QGridLayout(scrollWidget)
    scrollLayout.setSpacing(4)
    scrollLayout.setContentsMargins(4, 4, 4, 4)

    buttonLayout = QHBoxLayout()

    # First layout: General options
    scrollLayout.addWidget(CreateSeparator( "Job Description" ),0,0,1,3)

    jobNameLabel = QLabel( "Job Name" )
    jobNameLabel.setToolTip("The name of your job. This is optional, and if left blank, it will default to 'Untitled'.")
    scrollLayout.addWidget(jobNameLabel,1,0)
    gui.jobNameWidget = QLineEdit( os.path.basename(FarmAPI.GetKatanaFileName()).split('.')[0] )
    scrollLayout.addWidget(gui.jobNameWidget, 1, 1, 1, 1 )

    commentLabel = QLabel( "Comment" )
    commentLabel.setToolTip("A simple description of your job. This is optional and can be left blank.")
    scrollLayout.addWidget(commentLabel,2,0)
    gui.commentWidget = QLineEdit( "" )
    scrollLayout.addWidget(gui.commentWidget, 2, 1, 1, 1 )

    departmentLabel = QLabel( "Department" )
    departmentLabel.setToolTip( "The department you belong to. This is optional and can be left blank." )
    scrollLayout.addWidget(departmentLabel, 3, 0)
    gui.departmentWidget = QLineEdit( "" )
    scrollLayout.addWidget(gui.departmentWidget, 3, 1, 1, 1 )

    # Second layout: Job options
    scrollLayout.addWidget(CreateSeparator( "Job Options" ),4,0,1,3)

    pools = submissionInfo["Pools"]
    poolLabel = QLabel( "Pool" )
    poolLabel.setToolTip( "The pool that your job will be submitted to." )
    scrollLayout.addWidget(poolLabel, 5, 0)

    gui.poolsWidget = QComboBox()
    gui.poolsWidget.addItems(pools)
    scrollLayout.addWidget(gui.poolsWidget, 5, 1 )

    secondPoolLabel = QLabel( "Secondary Pool" )
    secondPoolLabel.setToolTip( "The secondary pool lets you specify a pool to use if the primary pool does not have any available Workers." )
    scrollLayout.addWidget(secondPoolLabel, 6, 0 )

    gui.secondPoolsWidget = QComboBox()
    gui.secondPoolsWidget.addItems(pools)
    scrollLayout.addWidget(gui.secondPoolsWidget, 6, 1 )

    groups = submissionInfo[ "Groups" ]
    groupLabel = QLabel( "Group" )
    groupLabel.setToolTip( "The group that your job will be submitted to." )
    scrollLayout.addWidget(groupLabel, 7, 0)

    gui.groupWidget = QComboBox()
    gui.groupWidget.addItems(groups)
    scrollLayout.addWidget(gui.groupWidget, 7, 1)

    priorityLabel = QLabel( "Priority" )
    priorityLabel.setToolTip( "A job can have a numeric priority from 0 to 100, where 0 is the lowest priority and 100 is the highest." )
    scrollLayout.addWidget(priorityLabel, 8, 0)

    maxPriority = submissionInfo["MaxPriority"]

    gui.priorityBox = QSpinBox()
    gui.priorityBox.setMinimum(0)
    gui.priorityBox.setMaximum( maxPriority )
    scrollLayout.addWidget(gui.priorityBox, 8, 1)

    taskTimeoutLabel = QLabel( "Task Timeout" )
    taskTimeoutLabel.setToolTip( "The number of minutes a Worker has to render a task for this job before it requeues it. Specify 0 for no limit." )
    scrollLayout.addWidget(taskTimeoutLabel, 9, 0)

    gui.taskTimeoutBox = QSpinBox()
    gui.taskTimeoutBox.setMinimum(0)
    gui.taskTimeoutBox.setMaximum(10000)
    scrollLayout.addWidget(gui.taskTimeoutBox, 9, 1)

    concurrentTasksLabel = QLabel( "Concurrent Tasks" )
    concurrentTasksLabel.setToolTip("The number of tasks that can render concurrently on a single Worker. This is useful if the rendering application only uses one thread to render and your Workers have multiple CPUs.")
    scrollLayout.addWidget(concurrentTasksLabel, 10, 0 )
    gui.concurrentTasksWidget = QSpinBox( )
    scrollLayout.addWidget(gui.concurrentTasksWidget, 10, 1)
    gui.concurrentTasksWidget.setMinimum(1)
    gui.concurrentTasksWidget.setMaximum(16)
    gui.limitTasksSlaveLimit = QCheckBox( "Limit Tasks To Worker's Task Limit" )
    gui.limitTasksSlaveLimit.setToolTip( "If you limit the tasks to a Worker's task limit, then by default, the Worker won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual Workers by an administrator." )
    scrollLayout.addWidget(gui.limitTasksSlaveLimit, 10, 2)

    machineLimitLabel = QLabel( "Machine Limit" )
    machineLimitLabel.setToolTip("Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.")
    scrollLayout.addWidget( machineLimitLabel, 11, 0 )

    gui.machineLimitWidget = QSpinBox()
    scrollLayout.addWidget(gui.machineLimitWidget, 11, 1)
    gui.isBlackListWidget = QCheckBox( "Machine List Is A Deny List" )
    gui.isBlackListWidget.setToolTip("You can force the job to render on specific machines by using an allow list, or you can avoid specific machines by using a deny list.")
    scrollLayout.addWidget(gui.isBlackListWidget, 11, 2)

    machineListLabel = QLabel( "Machine List" )
    machineListLabel.setToolTip("The list of machines on the deny list or allow list.")
    scrollLayout.addWidget( machineListLabel, 12, 0 )

    machineListLayout = QHBoxLayout()
    gui.machineListWidget = QLineEdit( "" )
    machineListLayout.addWidget(gui.machineListWidget)
    getMachineListWidget = QPushButton( "..." )
    getMachineListWidget.pressed.connect( lambda: BrowseMachineList(gui.machineListWidget) )
    machineListLayout.addWidget(getMachineListWidget)
    scrollLayout.addLayout( machineListLayout, 12, 1, 1, 2 )

    limitsLabel = QLabel( "Limits" )
    limitsLabel.setToolTip("The Limits that your job requires.")
    scrollLayout.addWidget( limitsLabel, 13, 0 )
    limitsLayout = QHBoxLayout()
    gui.limitsWidget = QLineEdit( "" )
    limitsLayout.addWidget(gui.limitsWidget)
    getLimitsWidget = QPushButton( "..." )
    getLimitsWidget.pressed.connect( lambda: BrowseLimitList(gui.limitsWidget) )
    limitsLayout.addWidget(getLimitsWidget)
    scrollLayout.addLayout( limitsLayout, 13, 1, 1, 2 )

    dependenciesLabel = QLabel( "Dependencies" )
    dependenciesLabel.setToolTip("Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering.")
    scrollLayout.addWidget( dependenciesLabel, 14, 0 )
    dependenciesLayout = QHBoxLayout()
    gui.dependenciesWidget = QLineEdit( "" )
    dependenciesLayout.addWidget(gui.dependenciesWidget)
    getDependenciesWidget = QPushButton( "..." )
    getDependenciesWidget.pressed.connect( lambda: BrowseDependencyList(gui.dependenciesWidget) )
    dependenciesLayout.addWidget(getDependenciesWidget)
    scrollLayout.addLayout( dependenciesLayout, 14, 1, 1, 2 )

    onJobCompleteLabel = QLabel( "On Job Complete" )
    onJobCompleteLabel.setToolTip("If desired, you can automatically archive or delete the job when it completes.")
    scrollLayout.addWidget( onJobCompleteLabel, 15, 0 )
    gui.onJobCompleteWidget = QComboBox( )
    gui.onJobCompleteWidget.addItems(["Nothing", "Archive", "Delete"])
    scrollLayout.addWidget(gui.onJobCompleteWidget, 15, 1)
    gui.submitSuspendedWidget = QCheckBox( "Submit Job as Suspended" )
    gui.submitSuspendedWidget.setToolTip( "If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render.")
    scrollLayout.addWidget(gui.submitSuspendedWidget, 15, 2)

    # Third layout: Katana options
    scrollLayout.addWidget(CreateSeparator( "Katana Options" ),16,0,1,3)

    frameRangeLabel = QLabel( "Frame Range" )
    frameRangeLabel.setToolTip("The list of frames to render.")
    scrollLayout.addWidget( frameRangeLabel, 17, 0 )
    gui.frameRangeWidget = QLineEdit( "" ) # Populate based on frame range
    scrollLayout.addWidget( gui.frameRangeWidget, 17, 1, 1, 1 )

    frameRange = FarmAPI.GetSceneFrameRange()
    gui.frameRangeWidget.setText( str(frameRange['start']) + "-" + str(frameRange['end']) )

    gui.submitSceneBox = QCheckBox( "Submit Katana Scene File" )
    gui.submitSceneBox.setToolTip( "If this option is enabled, the scene file will be submitted with the job, and then copied locally to the Worker machine during rendering." )
    scrollLayout.addWidget(gui.submitSceneBox, 17, 2 )

    framesPerTaskLabel = QLabel( "Frames Per Task" )
    framesPerTaskLabel.setToolTip( "This is the number of frames that will be rendered at a time for each job task." )
    scrollLayout.addWidget( framesPerTaskLabel, 18, 0 )
    gui.framesPerTaskWidget = QSpinBox(  )
    gui.framesPerTaskWidget.setMinimum(1)
    scrollLayout.addWidget( gui.framesPerTaskWidget, 18, 1, 1, 1 )

    gui.useWorkingDirectory = QCheckBox( "Use Working Directory" )
    gui.useWorkingDirectory.setToolTip( "If enabled, the current working directory will be used during rendering. This is required if your Katana project file contains relative paths." )
    gui.useWorkingDirectory.setChecked(True)
    scrollLayout.addWidget( gui.useWorkingDirectory, 18, 2 )

    renderNodeSelectLabel = QLabel( "Render Node Submission" )
    renderNodeSelectLabel.setToolTip( "Choose to render the whole scene, render all nodes as separate jobs, or render separate nodes" )
    scrollLayout.addWidget( renderNodeSelectLabel, 19, 0 )

    gui.renderSelectBox = QComboBox()
    gui.renderSelectBox.addItems( ["Submit All Render Nodes As Separate Jobs", "Select Render Node"] )
    scrollLayout.addWidget( gui.renderSelectBox, 19, 1 )

    gui.includeImageWrite = QCheckBox( "Include ImageWrite Nodes" )
    gui.includeImageWrite.setToolTip( "If enabled, ImageWrite nodes will be included for submission." )
    scrollLayout.addWidget( gui.includeImageWrite, 19, 2 )

    renderNodeLabel = QLabel( "Render Node" )
    renderNodeLabel.setToolTip( "Set the render node to render with, or leave blank to use the node already set." )
    scrollLayout.addWidget( renderNodeLabel, 20, 0 )

    gui.frameDependent = QCheckBox( "Submit Jobs As Frame Dependent" )
    gui.frameDependent.setToolTip( "If enabled, the Katana Job(s) will have Frame Dependencies. If your scene contains static content, do not use!" )
    scrollLayout.addWidget( gui.frameDependent, 20, 2 )

    gui.renderNodeBox = QComboBox()
    gui.renderSelectBox.currentIndexChanged.connect( lambda: RenderSelectionChanged( gui.renderSelectBox, gui.renderNodeBox ) )
    scrollLayout.addWidget( gui.renderNodeBox, 20, 1)
    gui.renderNodeBox.setDisabled(True)
    # Submit button
    buttonLayoutSpacer = QSpacerItem( 0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum )
    buttonLayout.addItem( buttonLayoutSpacer )

    gui.pipelineToolStatusLabel = QLabel( "No Pipeline Tools Set" )
    gui.pipelineToolStatusLabel.setAlignment( QtCore.Qt.AlignCenter )
    buttonLayout.addWidget( gui.pipelineToolStatusLabel )
    pipelineToolsButton = QPushButton( "Pipeline Tools" )
    pipelineToolsButton.pressed.connect( lambda: PipelineToolsClicked( gui ) )
    buttonLayout.addWidget( pipelineToolsButton )

    submitButton = QPushButton( "Submit" )
    submitButton.pressed.connect( lambda: SubmitPressed(gui) )
    buttonLayout.addWidget( submitButton )

    scrollLayout.addLayout( buttonLayout,21,0,1,3 )

    verticalStretchLayout = QVBoxLayout()
    verticalStretchLayout.addStretch()
    scrollLayout.addLayout( verticalStretchLayout, 22, 0 )

    scrollArea = QScrollArea()
    scrollArea.setWidget(scrollWidget)
    scrollArea.setWidgetResizable(True)
    scrollArea.setFrameStyle(QFrame.NoFrame + QFrame.Plain)

    vLayout = QVBoxLayout()
    vLayout.setObjectName('vLayout')
    vLayout.addWidget(scrollArea)

    gui.setLayout(vLayout)

    LoadStickySettings( gui )
    try:
        pipelineToolStatusMessage = RetrievePipelineToolStatus( raiseOnExitCode=True )
    except subprocess.CalledProcessError as e:
        pipelineToolStatusMessage = HandlePipelineToolsCalledProcessError( e )
    UpdatePipelineToolStatusLabel( gui, pipelineToolStatusMessage )

    # Populate the render node drop down based on the effective check state
    # of the "Include ImageWrite Nodes" checkbox after sticky settings are applied
    PopulateRenderNodeDropDown(gui.includeImageWrite.isChecked(), gui.renderNodeBox)
    # We delay wiring up this signal handler until after the sticky settings are applied to avoid
    # rebuilding the drop-down list multiple times unnecessarily
    gui.includeImageWrite.stateChanged.connect(lambda checked: PopulateRenderNodeDropDown(checked, gui.renderNodeBox))

    # Check if this tab is part of a pane in the main window, or if it is contained in a floating pane
    if gui.window() != UI4.App.MainWindow.CurrentMainWindow():
        # Resize the floating pane's window to accommodate the tab's widgets
        requiredSize = scrollWidget.sizeHint()
        gui.window().resize(max(requiredSize.width() + 20, 200), min(requiredSize.height() + 40, 1000))

def PipelineToolsClicked( gui ):
    try:
        pipelineToolStatus = OpenIntegrationWindow( raiseOnExitCode=True )
    except SceneNotSavedError:
        ShowModalDialog("Pipeline Tools Error", "Scene not saved")
        return
    except subprocess.CalledProcessError as e:
        pipelineToolStatus = HandlePipelineToolsCalledProcessError( e )

    UpdatePipelineToolStatusLabel(gui, pipelineToolStatus )

def SubmitPressed( gui ):
    print( "Submitting Katana Render Job(s) To Deadline..." )

    WriteStickySettings( gui )

    # pre-flight submission checks
    scene = NodegraphAPI.GetSourceFile()
    if not scene:
        QMessageBox.information( gui, "No Scene File Found", "No Katana file has been set. Please save your work and reopen the submitter." )
        return

    renderNodeSelection = gui.renderSelectBox.currentText()
    items = get_output_nodes(gui.includeImageWrite.isChecked())
    if not items:
        QMessageBox.information( gui, "No Output Nodes", "No enabled Render or ImageWrite nodes found in project file. Ensure project file contains at least one such node." )
        return

    frames = gui.frameRangeWidget.text()
    if not frames:
        QMessageBox.information( gui, "No Frame Range Specified", "No Frame Range been set. Please specify at least one frame to render." )
        return

    submitScene = gui.submitSceneBox.isChecked()
    if not submitScene and CheckIsPathLocal(scene):
        selection = QMessageBox.question( gui, "Local Katana Scene Submission", "The Katana scene is local and is not being submitted with the job. Deadline Workers may not be able to find the Katana file. Do you wish to submit anyway?", QMessageBox.Yes, QMessageBox.No )
        if selection == QMessageBox.No:
            return

    numJobs = 1
    jobResults = ""

    #Tell Katana to update the derive parameters on all Render Nodes ( such as output paths )
    Nodes3DAPI.RenderNodeUtil.SyncAllOutputPorts()
    
    if renderNodeSelection == "Select Render Node":
        jobResults = WriteJobFilesAndSubmit(gui, scene, submitScene, NodegraphAPI.GetNode( str(gui.renderNodeBox.currentText()) ))
    elif renderNodeSelection == "Submit All Render Nodes As Separate Jobs":
        nodeToID = {}

        currJob = 0
        currNode = 0
        done = False
        numJobs = len(items)

        while not done:
            if RenderNodeReady( items[currNode], nodeToID ):
                dependentIDs = GetDependentIDString(items[currNode], nodeToID)
                currResult = WriteJobFilesAndSubmit(gui, scene, submitScene, items[currNode], currJob, dependentIDs, numJobs, framSettingOn=1)
                currJob += 1
                nodeToID[items[currNode].getName()] = GetJobIDFromJobResults(currResult)

                items.remove(items[currNode])
                currNode = 0
                done = not len(items)
                jobResults += currResult
            else:
                currNode += 1

    resultOutput = "Done submitting %d job(s)." % numJobs

    if numJobs == 1:
        resultOutput += "\n" + jobResults
    else:
        resultOutput += "\nPlease consult the Katana command-line log for complete details."
        print( jobResults )

    QMessageBox.information( gui, "Submission Results", resultOutput)

def WriteJobFilesAndSubmit( gui, scene, submitScene, renderNode, currJob=-1, dependentIDs="", totalJobs=1 , framSettingOn = 0):
    global submissionInfo

    deadlineHome = submissionInfo[ "UserHomeDir" ].strip()

    deadlineTemp = os.path.join( deadlineHome, "temp" )
    
    if currJob >= 0:
        jobFile = "katana_job_info%d.job" % currJob
    else:
        jobFile = "katana_job_info.job"

    jobInfoFilename = os.path.join( deadlineTemp, jobFile )
    with io.open( jobInfoFilename, "w", encoding="utf-8-sig" ) as fileHandle:
        jobName = gui.jobNameWidget.text()
        if currJob >= 0:
            jobName += " - " + renderNode.getName()

        fileHandle.write( "Plugin=Katana\n" )
        fileHandle.write( "Name=%s\n" % jobName )
        fileHandle.write( "Comment=%s\n" % gui.commentWidget.text() )
        fileHandle.write( "Department=%s\n" % gui.departmentWidget.text() )
        fileHandle.write( "Pool=%s\n" % gui.poolsWidget.currentText() )
        fileHandle.write( "SecondaryPool=%s\n" % gui.secondPoolsWidget.currentText() )
        fileHandle.write( "Group=%s\n" % gui.groupWidget.currentText() )
        fileHandle.write( "Priority=%s\n" % str( gui.priorityBox.value() ) )
        fileHandle.write( "TaskTimeoutMinutes=%s\n" % str( gui.taskTimeoutBox.value() ) )
        fileHandle.write( "ConcurrentTasks=%s\n" % str(gui.concurrentTasksWidget.value() ) )
        fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % str(gui.limitTasksSlaveLimit.isChecked()) )
        fileHandle.write( "MachineLimit=%s\n" % str(gui.machineLimitWidget.value() ) )
        if gui.isBlackListWidget.isChecked():
            fileHandle.write( "Blacklist=%s\n" % gui.machineListWidget.text() )
        else:
            fileHandle.write( "Whitelist=%s\n" % gui.machineListWidget.text() )

        fileHandle.write( "LimitGroups=%s\n" % gui.limitsWidget.text() )

        if len( gui.dependenciesWidget.text() ) and len( dependentIDs ):
            dependencies = gui.dependenciesWidget.text() + "," + dependentIDs
        else:
            dependencies = gui.dependenciesWidget.text() or dependentIDs

        fileHandle.write( "JobDependencies=%s\n" % dependencies )
        fileHandle.write( "IsFrameDependent=%s\n" % gui.frameDependent.isChecked() )
        fileHandle.write( "OnJobComplete=%s\n" % gui.onJobCompleteWidget.currentText() )

        if gui.submitSuspendedWidget.isChecked():
            fileHandle.write( "InitialStatus=Suspended\n" )

        fileHandle.write( "ChunkSize=%s\n" % str(gui.framesPerTaskWidget.value()) )
        if framSettingOn:
            framSetting = renderNode.getParameter("farmSettings")
            activeRange = framSetting.getChild("activeFrameRange")
            start = activeRange.getChild("start")
            end = activeRange.getChild("end")
            frameRange = "%s-%s" %(start.getValue(0), end.getValue(0))
            fileHandle.write( "Frames=%s\n" % frameRange )
        else:
            fileHandle.write( "Frames=%s\n" % gui.frameRangeWidget.text() )

        if totalJobs > 1:
            fileHandle.write( "BatchName=%s\n" % gui.jobNameWidget.text() )

        if renderNode.getType() == "Render":
            for i in range(Nodes3DAPI.RenderNodeUtil.GetNumRenderOutputs(renderNode)):
                output = Nodes3DAPI.RenderNodeUtil.GetRenderOutputLocation(renderNode, i)
                tempPath, tempFileName = os.path.split( output )
                tempFileName = GetPaddedPath(tempFileName)
                paddedPath = os.path.join(tempPath, tempFileName)
                fileHandle.write( "OutputFilename%d=%s\n" % ( i, paddedPath ) )

        elif renderNode.getType() == "ImageWrite":
            for i, port in enumerate(renderNode.getInputPorts()):
                output = renderNode.getParameter('inputs.' + port.getName() + '.file').getValue(1)
                tempPath, tempFileName = os.path.split( output )
                tempFileName = GetPaddedPath(tempFileName)
                paddedPath = os.path.join(tempPath, tempFileName)
                fileHandle.write( "OutputFilename%d=%s\n" % ( i, paddedPath ) )

        #######################################################################################################
        # SHOTGUN - FTRACK - DRAFT
        #######################################################################################################

        integrationSettingsFilename = os.path.join( deadlineTemp, "KatanaIntegrationSettings.txt" )

        groupBatch = False

        if "integrationSettingsPath" in integrationInfoKeyValues:
            integrationSettingsFilename = integrationInfoKeyValues["integrationSettingsPath"]

        if "extraKVPIndex" in integrationInfoKeyValues:
            kvpIndex = integrationInfoKeyValues["extraKVPIndex"]

        if "batchMode" in integrationInfoKeyValues:
            if integrationInfoKeyValues["batchMode"] == "True":
                groupBatch = True

        if os.path.isfile( integrationSettingsFilename ):
            integrationSettingsFile = open( integrationSettingsFilename, "r" )
            data = integrationSettingsFile.readlines()
            for line in data:
                fileHandle.write( line )
            integrationSettingsFile.close()
            os.remove( integrationSettingsFilename )

        if groupBatch and totalJobs == 1:
            fileHandle.write( "BatchName=%s\n" % gui.jobNameWidget.text() )

        #######################################################################################################
        # END SHOTGUN - FTRACK - DRAFT
        #######################################################################################################

    if currJob >= 0:
        pluginFile = "katana_plugin_info%d.job" % currJob
    else:
        pluginFile = "katana_plugin_info.job"

    pluginInfoFilename = os.path.join( deadlineTemp, pluginFile )
    with io.open( pluginInfoFilename, "w", encoding="utf-8-sig" ) as fileHandle:
        if not gui.submitSceneBox.isChecked():
            fileHandle.write( "KatanaFile=%s\n" % scene )

        fileHandle.write( "Version=%d\n" % version[0] )

        if gui.useWorkingDirectory.isChecked():
            fileHandle.write( "WorkingDirectory=%s\n" % os.getcwd() )
        else:
            fileHandle.write( "WorkingDirectory=\n" )

        fileHandle.write( "RenderNode=%s\n" % renderNode.getName() )
    ConcatenatePipelineSettingsToJob( jobInfoFilename, str(gui.jobNameWidget.text()) )

    arguments = [
        jobInfoFilename,
        pluginInfoFilename
    ]

    if submitScene:
        arguments.append( scene )
        
    results = CallDeadlineCommand( arguments, useArgFile=True )
    return results

#######################################################################################################
# SHOTGUN - FTRACK - DRAFT
#######################################################################################################
def ConcatenatePipelineSettingsToJob( jobInfoPath, batchName ):
    """
    Augments a staged job info submission file with the appropriate properties for the Pipeline Tool settings.
    :param jobInfoPath: The path to the staged job info submission file to modify.
    :param batchName: The name of the batch the job will be submitted to. Any downstream jobs created by Pipeline Tools
                      will be added to the same batch.
    """
    global submissionInfo
    jobWriterPath = os.path.join( submissionInfo["RepoDirs"]["submission/Integration/Main"], "JobWriter.py" )
    scenePath = NodegraphAPI.GetSourceFile()
    argArray = ["-ExecuteScript", jobWriterPath, "Katana", "--write", "--scene-path", scenePath, "--job-path", jobInfoPath, "--batch-name", batchName]
    CallDeadlineCommand( argArray, False )

def OpenIntegrationWindow():
    global submissionInfo
    integrationDir = submissionInfo["RepoDirs"]["submission/Integration/Main"].strip()
    scriptPath = os.path.join( integrationDir, "IntegrationUIStandAlone.py" )

class SceneNotSavedError(Exception):
    pass
def RetrievePipelineToolStatus( raiseOnExitCode=False ):
    """
    Grabs a status message from the JobWriter that indicates which pipeline tools have settings enabled for the current
    scene.
    :param raiseOnExitCode: Whether to raise a subprocess.CalledProcessError when a non-zero exit code is returned
                            from the deadline command process
    :raises subprocess.CalledProcessError: if raiseOnExitCode is True and the subprocess call returns a non-zero
                                           exit code
    :return:  The status message to be presented to the user depicting the Pipeline Tool status
    """
    global submissionInfo

    scenePath = NodegraphAPI.GetSourceFile()

    jobWriterPath = os.path.join(submissionInfo["RepoDirs"]["submission/Integration/Main"], "JobWriter.py")
    argArray = ["-ExecuteScript", jobWriterPath, "Katana", "--status", "--scene-path", scenePath]
    statusMessage = CallDeadlineCommand(argArray, hideWindow=False, raiseOnExitCode=raiseOnExitCode)
    return statusMessage

def UpdatePipelineToolStatusLabel( gui, statusMessage ):
    """
    Modifies the Pipeline Tool status label UI element with the supplied message
    :param gui: A reference to the GUI
    :param str statusMessage: A string representation of the Pipeline Tool status to present to the user
    """
    gui.pipelineToolStatusLabel.setText( statusMessage )

def HandlePipelineToolsCalledProcessError( exc ):
    """
    Generic error handling when the a pipeline tools script run via deadline command returns a non-zero exit code.

    Generates a technical error message for a given subprocess.CalledProcessError instance and displays it in the
    Katana console. Similarly, a human-readable error message is presented to the user in a modal dialog.

    The technical error message contains the full command-line arguments, exit code, and standard output from the
    called process.

    Returns a user-friendly error message that can be presented to the user in the pipeline tools status label

    :param exc: An instance of subprocess.CalledProcessError that is used to generate the technical error message
    :return: A user-friendly status message indicating there was a pipeline tools error
    """
    errorMsg = StringIO()
    errorMsg.write( "Pipeline Tools encountered an error - the command:" )
    errorMsg.write( os.linesep * 2 )
    errorMsg.write( exc.cmd )
    errorMsg.write( os.linesep * 2 )
    errorMsg.write( "return a non-zero (%d) exit code" % exc.returncode )

    if exc.output:
        errorMsg.write( " and the following output:" )
        errorMsg.write( os.linesep * 2 )
        errorMsg.write( exc.output )

    errorMsg = errorMsg.getvalue()
    # On Windows, print statements output to the console window that is created minimized when Katana launches
    print( errorMsg )

    # Display a human-readable generic error message
    ShowModalDialog( "Pipeline Tools Error",
                     "Pipeline Tools encountered an error. Check the Katana console for more detailed information." )

    return "Pipeline Tools Error"

def OpenIntegrationWindow( raiseOnExitCode=False ):
    """
    Opens the a dialog for viewing and modifying the job's pipeline tool settings. The dialog is launched in a
    deadline command subprocess. All settings are maintained by the JobWriter using a combination of the application
    name and the scene path.

    :param raiseOnExitCode: If True, a subprocess.CalledProcessError is raised when the call to deadline command has
                            a non-zero exit code.
    :raise SceneNotSavedError: If the scene is not saved
    :raises subprocess.CalledProcessError: If raiseOnExitCode is True and the subprocess yields a non-zero exit code
    :return: The effective status of the pipeline tools settings for the current scene.
    """
    global submissionInfo

    integrationPath = os.path.join( submissionInfo["RepoDirs"]["submission/Integration/Main"], "IntegrationUIStandAlone.py" )
    scenePath = NodegraphAPI.GetSourceFile()
    if not scenePath:
        raise SceneNotSavedError()
    argArray = ["-ExecuteScript", integrationPath, "-v", "2", "-d", "Katana", "Draft", "Shotgun", "FTrack", "--path", scenePath]
    try:
        pipelineToolStatus = CallDeadlineCommand(argArray, hideWindow=False, raiseOnExitCode=True)
    except subprocess.CalledProcessError as e:
        pipelineToolStatus = HandlePipelineToolsCalledProcessError( e )

    return pipelineToolStatus

#######################################################################################################
# END SHOTGUN - FTRACK - DRAFT
#######################################################################################################

def GetPaddedPath( path ):
    paddingRe = re.compile( r"\.([0-9]+)", re.IGNORECASE )
    
    paddingMatches = paddingRe.findall( path )
    if paddingMatches:
        paddingString = paddingMatches[ -1 ]
        paddingSize = len(paddingString)
        
        padding = ""
        while len(padding) < paddingSize:
            padding = padding + "#"
        
        path = RightReplace( path, paddingString, padding, 1 )
    
    return path

def RightReplace( s, old, new, occurrence ):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def RenderSelectionChanged( selectionBox, nodeBox ):
    nodeBox.setEnabled( selectionBox.currentText() == "Select Render Node" )

def PopulateRenderNodeDropDown(include_image_write_nodes, dropdown):
    dropdown.clear()
    dropdown.addItems([item.getName() for item in get_output_nodes(include_image_write_nodes)])

def CreateSeparator( text ):
    separator = QWidget()
    separator.resize( 308, 37 )
    sepLayout = QHBoxLayout(separator)
    sepLayout.setContentsMargins(0, 0, 0, -1)
    
    sepLabel = QLabel(separator)
    sizePolicy = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(sepLabel.sizePolicy().hasHeightForWidth())
    sepLabel.setSizePolicy(sizePolicy)
    font = QFont()
    font.setBold(True)
    sepLabel.setFont(font)
    sepLabel.setText(text)
    sepLayout.addWidget(sepLabel)
    
    sepLine = QFrame(separator)
    sepLine.setFrameShadow(QFrame.Sunken)
    sepLine.setFrameShape(QFrame.HLine)
    sepLayout.addWidget(sepLine)

    return separator

def GetDeadlineCommand( useDeadlineBg=False ):
    """
    Returns the path to DeadlineCommand.
    :param useDeadlineBg: If enabled this will return the path to DeadlineCommandBg instead of DeadlineCommand
    :return: The path to the DeadlineCommand Executable
    """
    deadlineBin = ""
    try:
        deadlineBin = os.environ[ 'DEADLINE_PATH' ]
    except KeyError:
        # if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        pass

    # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
    if deadlineBin == "" and os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with io.open( "/Users/Shared/Thinkbox/DEADLINE_PATH", encoding="utf-8" ) as f:
            deadlineBin = f.read().strip()

    exeName = "deadlinecommand"
    if useDeadlineBg:
        exeName += "bg"

    deadlineCommand = os.path.join( deadlineBin, exeName )

    return deadlineCommand

def CreateArgFile( arguments, tmpDir ):
    """
    Creates a utf-8 encoded file with each argument in arguments on a separate line.
    :param arguments: The list of arguments that are to be added to the file
    :param tmpDir: The directory that the file should be written to.
    :return: The path to the argument file that was created.
    """
    tmpFile = os.path.join( tmpDir, "args.txt" )

    with io.open( tmpFile, 'w', encoding="utf-8-sig" ) as fileHandle:
        fileHandle.write( "\n".join( arguments ) )

    return tmpFile

def CallDeadlineCommand(arguments, hideWindow=True, useArgFile=False, useDeadlineBg=False, raiseOnExitCode=False):
    """
    Run DeadlineCommand with the specified arguments returning the standard out
    :param arguments: The list of arguments that are to be run
    :param hideWindow: If enabled all popups will be hidden
    :param useArgFile: If enabled all arguments will be written to a file and then passed in to deadline command
    :param useDeadlineBg: If enabled DeadlineCommandbg will be used instead of DeadlineCommand
    :param raiseOnExitCode: If enabled, a non-zero return code will raise a subprocess.CalledProcessError
    :return: The stdout from the DeadlineCommand Call
    """
    deadlineCommand = GetDeadlineCommand( useDeadlineBg )
    tmpdir = None

    if useArgFile or useDeadlineBg:
        tmpdir = tempfile.mkdtemp()

    if useDeadlineBg:
        arguments = [ "-outputfiles", os.path.join( tmpdir, "dlout.txt" ), os.path.join( tmpdir, "dlexit.txt" ) ] + arguments

    startupinfo = None
    creationflags = 0

    if os.name == 'nt':
        if hideWindow:
            # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
            if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # still show top-level windows, but don't show a console window
            CREATE_NO_WINDOW = 0x08000000  # MSDN process creation flag
            creationflags = CREATE_NO_WINDOW

    if useArgFile:
        arguments = [ CreateArgFile( arguments, tmpdir ) ]

    arguments.insert( 0, deadlineCommand )

    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen( arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags )
    output, errors = proc.communicate()

    if raiseOnExitCode and proc.returncode != 0:
        try:
            # The quote function was moved to shutil in python 3
            from shutil import quote as shell_quote
        except ImportError:
            # In python 2, quote lived in the pipes module
            from pipes import quote as shell_quote
        cmd = ' '.join([shell_quote(arg) for arg in arguments])
        raise subprocess.CalledProcessError(proc.returncode, cmd, output)

    if useDeadlineBg:
        with io.open( os.path.join( tmpdir, "dlout.txt" ), 'r', encoding='utf-8' ) as fileHandle:
            output = fileHandle.read()

    if tmpdir:
        try:
            shutil.rmtree( tmpdir )
        except:
            print( 'Failed to remove temp directory: "%s"' % tmpdir )

    return output.strip()


def BrowseMachineList( machineListWidget ):
    output = CallDeadlineCommand(["-selectmachinelist", str(machineListWidget.text())], hideWindow=False, useArgFile=True, useDeadlineBg=True)
    output = output.replace("\r", "").replace("\n", "")
    if output != "Action was cancelled by user":
        machineListWidget.setText(output)

def BrowseLimitList( limitsWidget ):
    output = CallDeadlineCommand(["-selectlimitgroups", str(limitsWidget.text())], hideWindow=False, useArgFile=True, useDeadlineBg=True)
    output = output.replace("\r", "").replace("\n", "")
    if output != "Action was cancelled by user":
        limitsWidget.setText(output)

def BrowseDependencyList( dependenciesWidget ):
    output = CallDeadlineCommand(["-selectdependencies", str(dependenciesWidget.text())], hideWindow=False, useArgFile=True, useDeadlineBg=True)
    output = output.replace("\r", "").replace("\n", "")
    if output != "Action was cancelled by user":
        dependenciesWidget.setText(output)

def GetJobIDFromJobResults( results ):
    resultArray = results.split("\n")
    _id = [line for line in resultArray if line.startswith("JobID=") ]
    return _id[0].replace("JobID=", "")

def RenderNodeReady( renderNode, dct ):
    # A render node is ready if all its dependencies have been accounted for (and have therefore been submitted)
    deps = GetAllDependencyNames(renderNode)
    return set(deps) <= set(dct.keys())

def GetAllDependencyNames( renderNode ):
    # Get the names of all unique nodes renderNode is dependent on
    renderSettingsNodes = FarmAPI.GetSortedDependencies(renderNode)
    dependencies = renderSettingsNodes[len(renderSettingsNodes)-1].dependencies # The last index of GetSortedDependencies() contains the dependencies directly corresponding to the current node
    return list(set(dependencies))

def GetDependentIDString( renderNode, nodeIDDict ):
    ids = []

    deps = GetAllDependencyNames(renderNode)
    for dep in deps:
        ids.append(nodeIDDict[dep])

    return ",".join(ids)

def CheckIsPathLocal( path ):
    lowerPath = path.lower()
    return lowerPath.startswith( "c:" ) or lowerPath.startswith( "d:" ) or lowerPath.startswith( "e:" )

def GetStickySettingsFilePath():
    """
    Get the path to the file where we will store sticky settings
    :return: The path to the file for sticky settings
    """
    global submissionInfo

    deadlineHome = submissionInfo[ "UserHomeDir" ].strip()
    return os.path.join( deadlineHome, "settings", "katana_sticky.json" )

def ShowModalDialog(title, msg):
    msgBox = QMessageBox()
    msgBox.setWindowTitle(title)
    msgBox.setText(msg)
    msgBox.exec_()

def WriteStickySettings( gui ):
    """
    Writes the current settings from Submitter UI to the sticky settings file.
    :param gui: The user interface that we need to pull settings from.
    """
    global stickySettingWidgets, stickyWidgetSaveFunctions
    print( "Writing sticky settings..." )

    configFile = GetStickySettingsFilePath()

    stickySettings = {}

    for setting, widgetName in stickySettingWidgets.iteritems():
        try:
            widget = getattr( gui, widgetName )
            stickySettings[setting] = stickyWidgetSaveFunctions[ type( widget ) ]( widget )
        except AttributeError:
            print( traceback.format_exc() )

    try:
        fileContents = json.dumps( stickySettings, encoding="utf-8" )
        with io.open( configFile, "w", encoding="utf-8" ) as fileHandle:
            fileHandle.write( fileContents.decode("utf-8") )
    except IOError:
        print( "Could not write sticky settings" )
        print( traceback.format_exc() )

def LoadStickySettings( gui ):
    """
    Reads in settings from the sticky settings file, then update the UI with the new settings
    :param gui: The user interface that we will set the settings on.
    """
    global stickySettingWidgets, stickyWidgetLoadFunctions
    configFile = GetStickySettingsFilePath()
    print( "Reading sticky settings from: %s" % configFile )

    stickySettings = None
    try:
        with io.open( configFile, "r", encoding="utf-8" ) as fileHandle:
            stickySettings = json.load( fileHandle, encoding="utf-8" )
    except IOError:
        print( "No sticky settings found. Using default settings." )
    except ValueError:
        print( "Invalid sticky settings. Using default settings." )
        print( traceback.format_exc() )
    except Exception:
        print( "Could not read sticky settings. Using default settings." )
        print( traceback.format_exc() )

    if stickySettings:
        for setting, value in stickySettings.iteritems():
            widgetName = stickySettingWidgets.get(setting)
            if widgetName:
                try:
                    widget = getattr(gui, widgetName)
                    stickyWidgetLoadFunctions[ type( widget ) ]( widget, value )
                except AttributeError:
                    print( traceback.format_exc() )
