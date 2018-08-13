// Decompiled with JetBrains decompiler
// Type: Block
// Assembly: Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null
// MVID: 9389A4AF-DACD-4250-864C-FFB1C86AE6D0
// Assembly location: SteamLibrary\steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data\Managed\Assembly-CSharp.dll

using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class Block
{
    #region Members

    public int distanceToStreet = 1000;
    public List<int> inputs = new List<int>();
    public List<int> outputs = new List<int>();
    public List<float> inputsAmounts = new List<float>();
    public List<float> outputsAmounts = new List<float>();
    public List<int> optionalInputs = new List<int>();
    public List<float> optionalInputsAmounts = new List<float>();
    private int callOnce = 1;
    private int callOnce2 = 1;
    private int cantiliverAmmount = 1000;
    public List<int> myAgents = new List<int>();
    public List<string> allAgentFunctionsString = new List<string>();
    public List<string> agentFunctionsToCall = new List<string>();
    public List<int> intsForfunctionsToCall = new List<int>();
    public List<int> intsForfunctionsToCall2 = new List<int>();
    public List<int> intsForfunctionsToCall3 = new List<int>();
    public List<int> intsForfunctionsToCall4 = new List<int>();
    public int myParentID = -1;
    public int maxDecay = 5;
    public bool doDecay = true;
    public bool needsAccessToProduce = true;
    public List<int> myConnectionsList = new List<int>();
    public List<int> myWalkableConnectionsList = new List<int>();
    public List<int> allNeighbors = new List<int>();
    public List<int> synergyBlocks = new List<int>();
    public List<float> synergyAmounts = new List<float>();
    public List<Block.SubCategory> synergyBlockCategories = new List<Block.SubCategory>();
    public List<float> synergyCategoriesAmounts = new List<float>();
    private int lastMonth = -1;
    public int agentInhabitingID = -1;
    public int levelOfFinish = 3;
    public int inspectDecay = 30;
    public float produceFactor = 1f;
    public float eventModifier = 1f;
    public float rateOfProductionModif = 1f;
    public float realRateOfProduction = 1f;
    public float oldrealRateOfProduction = 1f;
    public List<int> customRegenBlocks = new List<int>();
    public List<int> customRegenBlocksAmmounts = new List<int>();
    public GameObject geometry;
    public GameObject altGeo1;
    public GameObject altGeo2;
    public float chance1;
    public float chance2;
    public bool haveAlt1;
    public bool haveAlt2;
    public Texture altTexture1;
    public Texture altTexture2;
    public Texture AltWhite1;
    public Texture AltWhite2;
    public GameObject ghostGeo;
    public Sprite icon;
    private Manager myManager;
    public string alias_spanish;
    public string description_spanish;
    public string alias_japanese;
    public string description_japanese;
    public string alias_french;
    public string description_french;
    public string alias_german;
    public string description_german;
    public string alias_italian;
    public string description_italian;
    public string alias_portugese;
    public string description_portugese;
    public string alias_korean;
    public string description_korean;
    public string alias_chinese;
    public string description_chinese;
    public string alias_russian;
    public string description_russian;
    public string alias_hungarian;
    public string description_hungarian;
    public string alias_spanish_d;
    public string description_spanish_d;
    public string alias_japanese_d;
    public string description_japanese_d;
    public string alias_french_d;
    public string description_french_d;
    public string alias_german_d;
    public string description_german_d;
    public string alias_italian_d;
    public string description_italian_d;
    public string alias_portugese_d;
    public string description_portugese_d;
    public string alias_korean_d;
    public string description_korean_d;
    public string alias_chinese_d;
    public string description_chinese_d;
    public string alias_russian_d;
    public string description_russian_d;
    public string alias_hungarian_d;
    public string description_hungarian_d;
    public int blockToCopy;
    public Block.Category category;
    public int ID;
    public int IDinArray;
    public int moneyCost;
    public int upKeep;
    public string myName;
    public bool isWalkable;
    public bool allowUpper;
    public bool allowLeft;
    public bool allowRight;
    public bool allowFront;
    public bool allowBack;
    public int direction;
    public bool connectForward;
    public bool connectBack;
    public bool connectLeft;
    public bool connectRight;
    public bool connectUpperForward;
    public bool connectUpperBack;
    public bool connectUpperLeft;
    public bool connectUpperRight;
    public bool currentConnectForward;
    public bool currentConnectBack;
    public bool currentConnectLeft;
    public bool currentConnectRight;
    public bool currentConnectUpperForward;
    public bool currentConnectUpperBack;
    public bool currentConnectUpperLeft;
    public bool currentConnectUpperRight;
    public string toolTipHeader;
    public string toolTipContent;
    private bool isAccessible;
    private bool streetAccess;
    public bool upperLevelAccess;
    public bool lowerLevelAccess;
    public bool inhabitable;
    public float rateOfProduction;
    public bool staticOutput;
    public float internalClock;
    public int idX;
    public int idY;
    public int idZ;
    private int heapIndex;
    public int gCost;
    public int hCost;
    public Vector3 worldPosition;
    public Block parent;
    public int myType;
    public int decay;
    public bool doneSwapping;
    public string blockToSwap;
    public GameObject decayGeo;
    public string decayName;
    public string decayComment;
    public bool isDead;
    public Texture colorMat;
    public Texture whiteMat;
    public Texture colorMatDecay;
    public Texture whiteMatDecay;
    public AudioClip creationSound;
    public AudioClip pokeSound;
    public bool producedLastTurn;
    public float resourcesPerSecond;
    public bool needsSoil;
    public bool doesntRotate;
    public bool doesntDecay;
    public bool localVariance;
    public bool doubleHeight;
    public bool tripleHeight;
    public bool inhabited;
    public int[] myConnections;
    private bool willDie;
    public Block.SubCategory subCategory;
    public float synergy;
    public float prevSynergy;
    public bool weatherVarience;
    public float summerModif;
    public float winterModif;
    public float fallModif;
    public float springModif;
    private bool tick;
    private bool agentCreated;
    public int updatePropagation;
    public int biodiversityAcum;
    public int landValAcum;
    public int biodiversity;
    public int bioRadius;
    public int landvalue;
    public int landVRadius;
    public bool indestructible;
    public int regeneratedCount;
    public int inspectedCount;
    public int hoverCount;
    public bool produceAtStart;
    public bool someOnesHome;
    public GameObject agentGO;
    public Material mainMaterial;
    public Material decayMaterial;
    public bool customRegen;
    private float rSeed;

    #endregion

    public enum Category
    {
        EMPTY,
        PUBLIC_SPACE,
        PRODUCTION,
        BUILDINGS,
        ORGANIC,
        DECAY,
        ADV_PUBLICSPACE,
        ADV_PRODUCTION,
        ADV_BUILDINGS,
        ADV_ORGANIC,
        WILD_TILES,
        ADV_PUBLIC_2,
        ADV_PROD_2,
        ADV_BUILD_2,
        ADV_ORGANIC_2,
        BUSY,
    }

    public enum SubCategory
    {
        _EMPTY,
        TREES,
        HOUSING,
        FARMS,
        INDUSTRY,
        COMMERCE,
        SPECIAL,
        PUBLIC_SPACE,
        PARK,
        SCENIC,
        HOTEL,
        VERTICAL_CIRC,
    }
}
