#from collections import OrderedDict
#for wsDtSegmentation
#from ilastik.applets.wsdt.wsdtApplet import WsdtApplet
#for OpLabelPipeline
#from lazyflow.roi import determineBlockShape

#from lazyflow.utility import OrderedSignal
#from lazyflow.roi import roiToSlice, sliceToRoi
#from lazyflow.operators import OpBlockedArrayCache, OpValueCache
#from lazyflow.operators.generic import OpPixelOperator, OpSingleChannelSelector
#for the LabelPipeline
#from lazyflow.operators import OpCompressedUserLabelArray

import numpy as np
import vigra

from lazyflow.graph import Operator, InputSlot, OutputSlot
from ilastik.applets.pixelClassification.opPixelClassification import OpLabelPipeline
#for caching the data of the watershed algorithm
from ilastik.applets.thresholdTwoLevels.opThresholdTwoLevels import _OpCacheWrapper

from ilastik.utility.VigraIlastikConversionFunctions import removeChannelAxis, addChannelAxis, getArray, evaluateSlicing

import logging
logger = logging.getLogger(__name__)


class OpWatershedSegmentation(Operator):
    """
    Initialize the parameters for the calculations (and Gui)
    Provide execution function for the execution of the watershed algorithm

    The names of slots are explained below
    """
    #TODO in doku fuer nutzung aufnehmen
    #seeds muessen 1, 2, 3 sein, also kann man auch 120 180, etc verwenden, 
    #rest aussen rum muss schwarz=0 sein
    #bei den membranen: die membrane selbst muessen 255 sein und der rest 0=schwarz
    #help(vigra.analysis.watershedsNew)

    ############################################################
    # Inputslots for inputs from other applets
    ############################################################
    RawData             = InputSlot() # Used by the GUI for display only
    Boundaries          = InputSlot() # for displaying as layer and as input for the watershed algorithm 
    Seeds               = InputSlot(optional=True) #for displaying in layer only
    CorrectedSeedsIn    = InputSlot(optional=True) #deals as input for the LabelChange stuff 

    SeedsExist          = InputSlot(optional=True, value=True) #default that seeds exist

    ############################################################
    # Inputslots for Internal Parameter Usage (don't change anything here)
    ############################################################
    ShowWatershedLayer  = InputSlot(value=False)
    UseCachedLabels     = InputSlot(value=False)

    ############################################################
    # watershed algorithm parameters (optional)
    ############################################################
    # a list of options can be found in function: prepareInputParameter
    WSNeighbors         = InputSlot(value="direct")
    WSMethod            = InputSlot(value="RegionGrowing")
    # default values
    WSTerminate         = InputSlot(value=vigra.analysis.SRGType.CompleteGrow)
    WSMaxCost           = InputSlot(value=0)


    ############################################################
    # Output Slots
    ############################################################
    #for the labeling
    CorrectedSeedsOut   = OutputSlot() # Labels from the user, used as seeds for the watershed algorithm
    WatershedCalc       = OutputSlot()
    #Cached Output of watershed should be the output in a layer, nothing more
    WSCCOCachedOutput   = OutputSlot()  # For the GUI (blockwise-access)

    ############################################################
    # Watershed: For serialization (saving in cache) of the watershed Output
    ############################################################
    WSCCOInputHdf5      = InputSlot(optional=True)
    WSCCOOutputHdf5     = OutputSlot()
    WSCCOCleanBlocks    = OutputSlot()


    ############################################################
    # Label slots (for the LabelListModel)
    ############################################################

    # GUI-only (not part of the pipeline, but saved to the project)
    LabelNames          = OutputSlot()
    LabelColors         = OutputSlot()
    PmapColors          = OutputSlot()

    NonZeroBlocks       = OutputSlot()



    def __init__(self, *args, **kwargs):
        super( OpWatershedSegmentation, self ).__init__(*args, **kwargs)

        # Default values for the slots, where the Names of the Labels for the 
        # LabelListModel, the color and the pixelMap is saved in
        self.LabelNames.setValue( [] )
        self.LabelColors.setValue( [] )
        self.PmapColors.setValue( [] )

        ############################################################
        # Label-Pipeline setup = WSLP
        ############################################################
        self.opWSLP = OpWatershedSegmentationLabelPipeline(parent=self)
        #Input
        self.opWSLP.RawData     .connect( self.RawData )
        self.opWSLP.SeedInput   .connect( self.CorrectedSeedsIn )
        #Output
        self.CorrectedSeedsOut  .connect( self.opWSLP.SeedOutput )
        # (optional)
        self.NonZeroBlocks      .connect( self.opWSLP.NonZeroBlocks )

        ############################################################
        # watershed calculations = WSC
        ############################################################
        self.opWSC  = OpWatershedSegmentationCalculation( parent=self)
        #Input
        self.opWSC.Boundaries   .connect( self.Boundaries )
        self.opWSC.Seeds        .connect( self.CorrectedSeedsOut )
        #Input Parameters (optional)
        self.opWSC.Neighbors    .connect( self.WSNeighbors )
        self.opWSC.Method       .connect( self.WSMethod )
        self.opWSC.MaxCost      .connect( self.WSMaxCost )
        self.opWSC.Terminate    .connect( self.WSTerminate )
        #Output
        self.WatershedCalc.connect( self.opWSC.Output )

        ############################################################
        # watershed calculations cached output = WSCCO
        ############################################################
        #cache our own output, don't propagate from internal operator
        self._cache = _OpCacheWrapper(parent=self)
        self._cache.name = "OpWatershedSegmentation.OpCacheWrapper"
        # use this output of the cache for displaying in a layer only
        self.WSCCOCachedOutput.connect(self._cache.Output)

        # Serialization slots
        self._cache.InputHdf5.connect(self.WSCCOInputHdf5)
        self.WSCCOCleanBlocks.connect(self._cache.CleanBlocks)
        self.WSCCOOutputHdf5.connect(self._cache.OutputHdf5)

        # the crux, where to define the Cache-Data
        self._cache.Input.connect(self.WatershedCalc)


    def setupOutputs(self):
        self.LabelNames.meta.dtype  = object
        #self.LabelNames.meta.shape = (1,)
        self.LabelNames.meta.shape  = (1,)
        self.LabelColors.meta.dtype = object
        self.LabelColors.meta.shape = (1,)
        self.PmapColors.meta.dtype  = object
        self.PmapColors.meta.shape  = (1,)


        ############################################################
        # For serialization 
        ############################################################
        # force the cache to emit a dirty signal 
        # (just taken from applet thresholdTwoLevel)
        self._cache.Input.connect(self.WatershedCalc)
        self._cache.Input.setDirty(slice(None))


        #for testing 
        print self.WSMethod.value

    
    def execute(self, slot, subindex, roi, result):
        pass
        
    def propagateDirty(self, slot, subindex, roi):
        pass

    def setInSlot(self, slot, subindex, roi, value):
        pass


class OpWatershedSegmentationLabelPipeline( Operator ):
    """
    operator class, that handles the Label Pipeline and the connections to it
    the opLabelPipeline handles the connections to the opCompressedUserLabelArray, 
    which is responsable for everything
    """
    RawData     = InputSlot()
    SeedInput   = InputSlot()
    SeedOutput  = OutputSlot()
    NonZeroBlocks = OutputSlot()
    
    
    def __init__(self, *args, **kwargs):
        super( OpWatershedSegmentationLabelPipeline, self ).__init__( *args, **kwargs )
        
        self.opLabelPipeline = OpLabelPipeline(parent=self)
        self.opLabelPipeline.RawImage.connect( self.RawData )
        self.opLabelPipeline.LabelInput.connect( self.SeedInput )
        self.opLabelPipeline.DeleteLabel.setValue( -1 )

        #Output
        self.SeedOutput.connect( self.opLabelPipeline.Output )
        self.NonZeroBlocks.connect( self.opLabelPipeline.nonzeroBlocks )

    def setupOutputs(self):
        '''
        self.SeedOutput.meta.assignFrom(self.SeedInput.meta)
        # output of the vigra.analysis.watershedNew is uint32, therefore it should be uint 32 as
        # well, otherwise it will break with the cached image 
        self.SeedOutput.meta.dtype = np.uint8
        #only one channel as output
        #self.SeedOutput.meta.shape = self.Boundaries.meta.shape[:-1] + (1,)
        #TODO maybe bad with more than 255 labels
        #self.SeedOutput.meta.drange = (0,255)
        '''
        pass

    def setInSlot(self, slot, subindex, roi, value):
        pass

    def execute(self, slot, subindex, roi, result):
        assert False, "Shouldn't get here.  Output is assigned a value in setupOutputs()"

    def propagateDirty(self, slot, subindex, roi):
        pass    



class OpWatershedSegmentationCalculation( Operator ):
    """
    operator class, that handles the input and output of calculation
    and the calculation itself
    """
    #input slot
    Boundaries  = InputSlot()
    Seeds       = InputSlot()


    #optional parameter input slots
    Neighbors   = InputSlot(optional=True)
    Method      = InputSlot(optional=True)
    MaxCost     = InputSlot(optional=True)
    Terminate   = InputSlot(optional=True)
    # if not connected, use the default-values. 
    # for more information, see function: prepareInputParameter 

    #output slot
    Output      = OutputSlot()


    def __init__(self, *args, **kwargs):
        super( OpWatershedSegmentationCalculation, self ).__init__( *args, **kwargs )


    def setupOutputs(self):
        self.Output.meta.assignFrom(self.Boundaries.meta)
        # output of the vigra.analysis.watershedNew is uint32, therefore it should be uint 32 as
        # well, otherwise it will break with the cached image 
        # UPDATE: actually, this behaviour changed during development, so that uint8 is correct 
        self.Output.meta.dtype = np.uint8
        #only one channel as output
        self.Output.meta.shape = self.Boundaries.meta.shape[:-1] + (1,)
        #TODO maybe bad with more than 255 labels
        self.Output.meta.drange = (0,255)

    def setInSlot(self, slot, subindex, roi, value):
        pass

    def execute(self, slot, subindex, roi, result):
        #assert False, "Shouldn't get here.  Output is assigned a value in setupOutputs()"
        pass

    def propagateDirty(self, slot, subindex, roi):
        pass    



    def execWatershedAlgorithm(self):
        """
        handles the execution of the watershed algorithm 
        """
        
        seeds               = getArray(self.Seeds)
        boundaries          = getArray(self.Boundaries)
        #boundaries, seeds  = self.getArrays()

        # necessary for vigra.analysis.watershedsNew
        boundaries, seeds   = self.arrayConversion(boundaries, seeds)

        # check the axes and return, whether the time is used and the number of the time axis
        (tUsed, tAxis)      = evaluateSlicing(self.Seeds)

        # needed for vigra to remove the channel axis
        seeds               = removeChannelAxis(seeds)
        boundaries          = removeChannelAxis(boundaries)
        #(boundaries, seeds) = self.removeChannelAxis(boundaries, seeds)


        # doesn't matter whether image is 2D or 3D, at least we do slicing over time
        # because 2D or 3D does vigra for us
        # slice over time
        if tUsed:
            labelImageArray = self.slicedWatershedAlgorithm(boundaries, seeds, tAxis)

            # no slicing
        else:
            (labelImageArray, maxRegionLabel) =\
                self.watershedAlgorithm(boundaries, seeds)

        # needed for ilastik to have a channel axis
        labelImageArray     = addChannelAxis(labelImageArray)

        # set the value of the OutputSlot to the calculated array
        self.Output.setValue(labelImageArray)

        ############################################################
        # BEGIN TODO
        ############################################################

        #TODO integrate process bar
        

        '''
        how to:::

         class ilastik.applets.base.applet.Applet(name, syncWithImageIndex=True, interactive=True)[source]

            progressSignal = None

                Progress signal. When the applet is doing something time-consuming, 
                this signal tells the shell to show a progress bar.
                Signature: emit(percentComplete, canceled=false)

        Note

        To update the progress bar correctly,
        the shell expects that progress updates always begin with at least
        one zero update and end with at least one 100 update. 
        That is: self.progressSignal.emit(0) ... more updates ... self.progressSignal.emit(100)
        '''
        ############################################################
        # END TODO
        ############################################################
        ''' 
        #for debugging
        tUsed = True if (tId < dims) else False
        zUsed = True if (zId < dims) else False

        if (cId >= dims or xId >= dims or yId >= dims):
            logger.info("no channel, x or y used in data; something is probably wrong")

        if (not tUsed and not zUsed):
            print "only x and y available"
            print "2D with one slice"

        if (not tUsed and zUsed):
            print "time not used, but z"
            print "use the whole dataset for 3D watershed"

        if (tUsed and not zUsed):
            print "time used, but not z"
            print "use the whole data sliced into 2D images for 2D watershed"

        if (tUsed and zUsed):
            print "time and z used"
            print "use 3D watershed with slices, means 3D watershed of each 3d image of the data-set"
        '''
        '''
        #self.Output.data = labelImage
        import h5py
        with h5py.File("testOutput", "w") as hf:
            hf.create_dataset("exported_data", data=labelImageArray)
        #print self.Seeds
        #print self.Output
        #of the last image
        #print maxRegionLabel
        #print boundaries.dtype
        #print seeds.dtype
        #print boundaries.shape
        #print seeds.shape
        '''

    ############################################################
    # the function, where the algorithm is executed itself
    ############################################################

    def watershedAlgorithm(self, boundaries, seeds=None):
        """
        :param boundaries: array that contains the boundaries
        :param seeds: array that contains the seeds
        :return: labelImage: (dtype = uint32) the array, that contains the results of the watershed algorithm;
            maxRegionLabel: the number of the watershed areas

        execute the watershed algorithm of vigra on the boundary and seed array
        therefore extract the parameters from InputSlots for the usage in this algorithm

        compare vigra.analysis.watershedsNew for more information on the meaning of the parameters
        """

        # detect the correct dimension for the watershed algorithm
        # if sliced, then the input is only a part of the series, 
        # and therefore the dimension is still correct
        method, neighbors, terminate, maxCost = self.prepareInputParameter(boundaries.ndim)
        '''
        print neighbors
        print method
        print terminate
        print maxCost
        '''

        #UnionFind doesn't support seeds and max_cost
        if (method == "UnionFind"):
            seeds = None
            maxCost = 0

        print "neighbors: '" + str(neighbors) + "'\nmethod: '" + str(method) + "'\nterminate: '" + str(terminate) + "'\nmaxCost: '" + str(maxCost) + "'\n"
        # watershedAlgoirthm itself
        (labelImage, maxRegionLabel) = vigra.analysis.watershedsNew(\
                image           = boundaries,
                seeds           = seeds,
                neighborhood    = neighbors,
                method          = method,
                terminate       = terminate,
                max_cost        = maxCost)



        return (labelImage, maxRegionLabel)



    ############################################################
    # helping functions
    ############################################################


    def arrayConversion(self, boundaries, seeds=None):
        """
        :param boundaries: array 1
        :param seeds: array2
        :return: boundaries, seeds
        convert the array in a numpy array that is necessary for vigra.analysis.watershedsNew
        """
        #boundaries
        # input image: uint8 or float32, (float32 includes more information)
        # because Turbo works with unint8 more effective
        if not (boundaries.dtype == np.uint8):
            boundaries     = boundaries.astype(np.float32)

        #for the seeds
        # uint32

        if not (seeds is None):
            seeds          = seeds.astype(np.uint32)
        return boundaries, seeds




    def slicedWatershedAlgorithm(self, boundaries, seeds=None, tAxis=0):
        """
        Uses watershedAlgorithm for the main algorithm execution
        but slices the data for it, so that that algorithm can be used easily.

        Handles the case where seeds can be None

        :param boundaries: the array, that contains the boundaries data
        :type boundaries: array
        :param seeds: the array, that contains the seeds data
        :type seeds: None or array
        :param tAxis: the dimension number of the time axis
        :type tAxis: int
        :return: labelImageArray: the concatenated watershed result of all slices 
        :rtype: array
        """
        labelImageArray = np.ndarray(shape=boundaries.shape, dtype=boundaries.dtype)
        for i in range(boundaries.shape[tAxis]):
            # iterate over the axis of the time
            boundariesSlice  = boundaries.take( i, axis=tAxis)

            # handle seeds = None or seeds = array
            if not (seeds is None):
                seedsSlice      = seeds.take(      i, axis=tAxis)
            else:
                seedsSlice      = None
            (labelImage, maxRegionLabel) =\
                    self.watershedAlgorithm(boundariesSlice, seedsSlice)

            # write in the correct column of the output array, 
            # because the dimensions must fit
            if (tAxis == 0):
                labelImageArray[i] = labelImage
            elif (tAxis == 1):
                labelImageArray[:,i] = labelImage
            elif (tAxis == 2):
                labelImageArray[:,:,i] = labelImage
            elif (tAxis == 3):
                labelImageArray[:,:,:,i] = labelImage
        return labelImageArray



    def prepareInputParameter(self, dimension):
        """
        :param dimension: the dimension to set the correct number of neighbors

        get the value of the inputSlots
        declare valid variables and their valid inputs
        check the input for correctness in comparison with the valid variables
        declare default values (if input not correct or unsufficient

        includes a list of correct/valid parameters
        """

        # get the value of the inputSlots
        ############################################################
        # check whether slot is ready (connected)
        # if yes, take its value
        # else use default value (None), conversion to default value later
        neighbors   = None
        method      = None
        terminate   = None
        maxCost     = None

        if self.Neighbors.ready():
            neighbors   = self.Neighbors    [:].wait()[0]
        
        if self.Method.ready():
            method      = self.Method       [:].wait()[0]

        if self.Terminate.ready():
            terminate   = self.Terminate    [:].wait()[0]

        if self.MaxCost.ready():
            maxCost     = self.MaxCost      [:].wait()[0]

        
        # declare valid variables and their valid inputs
        ############################################################

        # None is always allowed and will be transformed to default value later
        method0         = None
        method1         = "RegionGrowing"
        method2         = "Turbo"
        method3         = "UnionFind"
        methodArray     = [method0, method1, method2, method3]
        methodName      = "Method"

        neighbors0      = None
        neighbors1      = "direct"
        neighbors2      = "indirect"
        neighborsArray  = [neighbors0, neighbors1, neighbors2]
        neighborsName   = "Neighbors"

        terminate0      = None
        terminate1      = vigra.analysis.SRGType.CompleteGrow
        terminate2      = vigra.analysis.SRGType.KeepContours
        terminate3      = vigra.analysis.SRGType.StopAtThreshold
        terminateArray  = [terminate0, terminate1, terminate2, terminate3]
        terminateName   = "Terminate"

        #maxCost must be a number: int, long or float

        data =\
            [[method, methodArray, methodName],
            [neighbors, neighborsArray, neighborsName],
            [terminate, terminateArray, terminateName]]
        

        # check the input for correctness
        ############################################################

        #check method, neighbors, terminate for correctness
        for (parameter, array, name) in  data:
            if not (parameter in array):
                logger.info("Input " + name +" is wrong; use default configuration")
                parameter = None

        #maxCost must be a number (int, long, float)
        if (not isinstance(maxCost, (int, long, float))):
            logger.info("Input maxCost is wrong; use default configuration")
            maxCost = None


        # test combinations, that they fit together
        if ((terminate == terminate2 or terminate == terminate3) and not (method == method1)):
            logger.info("the chosen terminate criteria is incompatible with the given method,\
                    reset method and terminate to default")
            terminate   = None
            method      = None

        if ((terminate == terminate3) and maxCost is None):
            logger.info("MaxCost parameter must be set for the StopAtThreshold termination option")
            logger.info("use default termination")
            terminate   = None


        # declare default values
        ############################################################
        # method
        if method == None:
            method = method1

        # neighbors, depending on dimension
        if neighbors == None or neighbors == neighbors1:
            if dimension == 2:
                neighbors = 4
            else:
                neighbors = 6
        else:
            if dimension == 2:
                neighbors = 8
            else:
                neighbors = 26

        # terminate
        if terminate == None:
            terminate = terminate1

        # maxCost
        if maxCost == None:
            maxCost = 0


        return method, neighbors, terminate, maxCost

