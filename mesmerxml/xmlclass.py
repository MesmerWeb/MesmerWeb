__author__ = 'ciaosu'

from lxml import etree

def separate(str, ch):
    re = ''
    lines = str.splitlines()
    for line in lines:
        line = line.strip()
        if line:
            re = re + line + ch
    return re.rstrip()

class MesmerXML:
    control_options = [
        'printCellDOS',
        'printCellTransitionStateFlux',
        'printReactionOperatorColumnSums',
        'printGrainBoltzmann',
        'printGrainDOS',
        'printGrainkbE',
        'printGrainkfE',
        'printTSsos',
        'printGrainedSpeciesProfile',
        'printGrainTransitionStateFlux',
        'printReactionOperatorSizematrix',
        'printSpeciesProfile',
        'printTunnelingCoefficients',
        'printTunnellingCoefficients',
        'printCrossingCoefficients',
        'MaximumEvolutionTime',
        'testDOS',
        'testMicroRates',
        'testRateConstants',
        'useTheSameCellNumberForAllConditions',
        'hideInactive'
    ]
    def __init__(self, xml):
        try:
            self.root = etree.fromstring(xml)
        except:
            self.error = "syntax error"

        try:
            self.me_ns = self.root.nsmap['me']
            self.ns = self.root.nsmap[None]
            self.xsi_ns = self.root.nsmap['xsi']
        except:
            pass

        self.molecules = {}

    # read condition from xml to json data
    def read_condition(self, el):
        conditions = {}
        PTs = []

        try:
            # read bathGas
            bath_gas_node = el.xpath('.//me:bathGas', namespaces={'me': self.me_ns})[0]
            conditions['bathGas'] = bath_gas_node.text
            self.molecules[conditions['bathGas']]['type'] = 'bathGas'

            # read InitialPopulation
            init_population_node = el.xpath('.//me:InitialPopulation', namespaces={'me': self.me_ns})[0]
            conditions['initialPopulation'] = init_population_node[0].get('{%s}population' % self.me_ns)
            conditions['initialPopulationRef'] = init_population_node[0].get('ref')

            # read PTs
            pts_node = el.xpath('.//me:PTs', namespaces={'me': self.me_ns})[0]
            for pt in pts_node:
                if isinstance(pt, etree._Comment):
                    continue
                PTs.append({
                    'P': pt.get('{%s}P' % self.me_ns),
                    'T': pt.get('{%s}T' % self.me_ns)
                })
                conditions['units'] = pt.get('{%s}units' % self.me_ns)
        except:
            pass
        conditions['PTs'] = PTs
        return conditions


    # read control from xml to json data
    def read_control(self, el):
        control = {}
        options = {}
        for control_el in el:
            if isinstance(control_el, etree._Comment):
                continue
            control_el_tag = etree.QName(control_el).localname
            if control_el_tag == 'eigenvalues':
                control['eigenvalues'] = control_el.text
            elif control_el_tag == 'calcMethod':
                control['calcMethod'] = control_el.text
            else:
                try:
                    i = self.control_options.index(control_el_tag)
                    options[control_el_tag] = True
                except:
                    pass

        control['options'] = options
        return control


    # read modelParameters from xml to json data
    def read_model_parameters(self, el):
        model_parameters = {}
        for parameter_el in el:
            if isinstance(parameter_el, etree._Comment):
                continue
            parameter_el_tag = etree.QName(parameter_el).localname
            model_parameters[parameter_el_tag] = parameter_el.text
        return model_parameters

    # read molecule list from xml to data
    def read_molecule_list(self, el):
        molecule_list = []

        for molecule_el in el:
            if isinstance(molecule_el, etree._Comment):
                continue
            molecule_el_tag = etree.QName(molecule_el).localname

            if molecule_el_tag == "molecule":
                molecule = {}
                # read id
                molecule['id'] = molecule_el.get('id')
                self.molecules[molecule['id']] = molecule

                try:
                    # read properties
                    property_list = molecule_el.xpath('.//ns:propertyList', namespaces={'ns': self.ns})[0]
                    for e in property_list:
                        if isinstance(e, etree._Comment):
                            continue
                        key = e.get('dictRef').replace('me:', '')
                        value = e[0].text
                        molecule[key] = value

                    if molecule['vibFreqs']:
                        molecule['vibFreqs'] = separate(molecule['vibFreqs'], ' ')
                    if molecule['rotConsts']:
                        molecule['rotConsts'] = separate(molecule['rotConsts'], ' ')

                    # read DOSCMethod
                    dosc_method_node = molecule_el.xpath('.//me:DOSCMethod', namespaces={'me': self.me_ns})[0]
                    molecule['DOSCMethod'] = dosc_method_node.text if dosc_method_node.text else dosc_method_node.get('name')
                except:
                    pass
                molecule_list.append(molecule)
        return molecule_list


    # read molecule list from xml to data
    def read_reaction_list(self, el):
        reaction_list = []

        for reaction_el in el:
            if isinstance(reaction_el, etree._Comment):
                continue

            reaction = {}

            # read id
            reaction['id'] = reaction_el.get('id')

            # read reactant
            try:
                reactant_list = reaction_el.xpath('.//ns:reactant', namespaces={'ns': self.ns})
                for index, value in enumerate(reactant_list):
                    m = value[0]
                    reaction['R' + str(index+1) + 'Type'] = m.get('{%s}type' % self.me_ns)
                    reaction['R' + str(index+1) + 'Ref'] = m.get('ref')
                    self.molecules[m.get('ref')]['type'] = m.get('{%s}type' % self.me_ns)
            except:
                pass

            # read product
            try:
                product_list = reaction_el.xpath('.//ns:product', namespaces={'ns': self.ns})
                for index, value in enumerate(product_list):
                    m = value[0]
                    reaction['P' + str(index+1) + 'Type'] = m.get('{%s}type' % self.me_ns)
                    reaction['P' + str(index+1) + 'Ref'] = m.get('ref')
                    self.molecules[m.get('ref')]['type'] = m.get('{%s}type' % self.me_ns)
            except:
                pass

            # judge reaction type
            if len(reactant_list) == 1 and len(product_list) == 1:
                reaction['type'] = 'A -> B'
            elif len(reactant_list) == 1 and len(product_list) == 2:
                reaction['type'] = 'A -> B + C'
            elif len(reactant_list) == 2 and len(product_list) == 1:
                reaction['type'] = 'A + B -> C'
            else:
                reaction['type'] = 'A + B -> C + D'

            # read MCRCMethod
            try:
                mcrc_method = reaction_el.xpath('.//me:MCRCMethod', namespaces={'me': self.me_ns})[0]

                # RRKM
                if mcrc_method.get('name') == 'SimpleRRKM' or mcrc_method.text == 'SimpleRRKM':
                    reaction['MCRCMethod'] = 'SimpleRRKM'
                    transition_state = reaction_el.xpath('.//me:transitionState', namespaces={'me': self.me_ns})[0]
                    m = transition_state[0]
                    reaction['TRef'] = m.get('ref')
                    reaction['TType'] = m.get('type')
                    self.molecules[m.get('ref')]['type'] = m.get('type')

                # ILT parameters
                elif mcrc_method.get('{%s}type' % self.xsi_ns) == 'MesmerILT' or mcrc_method.text == 'MesmerILT':
                    pre_exponential = reaction_el.xpath('.//me:preExponential', namespaces={'me': self.me_ns})[0]
                    reaction['preExponential'] = pre_exponential.text;

                    activation_energy = reaction_el.xpath('.//me:activationEnergy', namespaces={'me': self.me_ns})[0]
                    reaction['activationEnergy'] = activation_energy.text

                    n_infinity = reaction_el.xpath('.//me:nInfinity', namespaces={'me': self.me_ns})[0]
                    reaction['nInfinity'] = n_infinity.text
            except:
                pass
            reaction_list.append(reaction)

        return reaction_list


    def to_json(self):
        json_data = {}
        for el in self.root:
            if isinstance(el, etree._Comment):
                continue
            tag = etree.QName(el).localname
            if tag == 'title':
                json_data['title'] = el.text

            # moleculeList element
            elif tag == 'moleculeList':
                json_data["moleculeList"] = self.read_molecule_list(el)

            # reactionList element
            elif tag == 'reactionList':
                json_data['reactionList'] = self.read_reaction_list(el)

            # conditions element
            elif tag == 'conditions':
                json_data['conditions'] = self.read_condition(el)

            # modelParameters element
            elif tag == 'modelParameters':
                json_data['modelParameters'] = self.read_model_parameters(el)

            # control element
            elif tag == 'control':
                json_data['control'] = self.read_control(el)
        return json_data
