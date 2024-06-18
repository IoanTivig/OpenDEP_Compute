### START IMPORTS ###
import math
### END IMPORTS ###


def complex_perm(freq, relperm, cond):
    return (relperm * 8.854 * 10**(-12)) - 1j * cond / (freq * 2 * math.pi)

def SS_model(freq, fitting_sish_particle_radius,fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond):
    #print ("fitting_sish_particle_radius: " + str(fitting_sish_particle_radius) + "Thickness: " + str(fitting_sish_membrane_thickness))
    return complex_perm(freq, fitting_sish_membrane_perm, fitting_sish_membrane_cond) * (((fitting_sish_particle_radius/(fitting_sish_particle_radius - 0.001*fitting_sish_membrane_thickness))**3 + 2 * ((complex_perm(freq, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) - complex_perm(freq, fitting_sish_membrane_perm, fitting_sish_membrane_cond))/(complex_perm(freq, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) + 2 * complex_perm(freq, fitting_sish_membrane_perm, fitting_sish_membrane_cond))))/((fitting_sish_particle_radius/(fitting_sish_particle_radius - 0.001*fitting_sish_membrane_thickness))**3 - ((complex_perm(freq, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) - complex_perm(freq, fitting_sish_membrane_perm, fitting_sish_membrane_cond))/(complex_perm(freq, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) + 2 * complex_perm(freq, fitting_sish_membrane_perm, fitting_sish_membrane_cond)))))

def sish_CMfactor(freq, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    return ((SS_model(freq, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) - complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond))/(SS_model(freq, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond) + 2 * complex_perm(freq, fitting_gen_buffer_perm, fitting_gen_buffer_cond))).real

def sish_DEPforce(freq, fitting_gen_fieldgrad, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    return 2.0 * math.pi * (fitting_gen_buffer_perm * 8.854 * 10**(-6)) * fitting_sish_particle_radius**3 * sish_CMfactor(freq, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond) * fitting_gen_fieldgrad

def sish_CMfactor_EF_unknown(freq, fitting_gen_fieldgrad, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    return sish_CMfactor(freq, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond) * fitting_gen_fieldgrad

def model_sish_CMfactor(frequencyList, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    CMfactorList = []
    for x in frequencyList:
        y = sish_CMfactor(x, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond)
        CMfactorList.append(y)

    return CMfactorList

def model_sish_DEPforce(frequencyList, fitting_gen_fieldgrad, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond):
    DEPforceList = []
    for x in frequencyList:
        y = sish_DEPforce(x, fitting_gen_fieldgrad, fitting_sish_particle_radius, fitting_sish_membrane_thickness, fitting_sish_membrane_perm, fitting_sish_membrane_cond, fitting_sish_cytoplasm_perm, fitting_sish_cytoplasm_cond, fitting_gen_buffer_perm, fitting_gen_buffer_cond)
        DEPforceList.append(y)

    return DEPforceList